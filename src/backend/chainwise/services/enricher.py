from chainwise.adapters import RPCClient, RPCError
from chainwise.config import NetworkConfig
from chainwise.models import TokenMetadata
from chainwise.observability import get_logger

logger = get_logger("chainwise.enricher")

_SYMBOL_SELECTOR = "0x95d89b41"
_DECIMALS_SELECTOR = "0x313ce567"


def _decode_uint(hex_data: str) -> int:
    return int(hex_data, 16)


def _decode_string(hex_data: str) -> str:
    """Decodes a single ABI-encoded dynamic `string` return value.

    Bounds-checked rather than trusting a well-formed response: a call to a
    non-existent contract or one that reverted with no data returns "0x",
    which Python's slicing wouldn't error on (offset=length=0 -> silently ""),
    masking a failure as a confirmed-empty symbol. Raising here routes it
    through the caller's existing except-and-skip instead.
    """
    data = bytes.fromhex(hex_data.removeprefix("0x"))
    if len(data) < 64:
        raise ValueError(f"dynamic string return too short: {len(data)} bytes")
    offset = int.from_bytes(data[0:32], "big")
    if offset + 32 > len(data):
        raise ValueError("string offset out of bounds")
    length = int.from_bytes(data[offset : offset + 32], "big")
    if offset + 32 + length > len(data):
        raise ValueError("string length out of bounds")
    return data[offset + 32 : offset + 32 + length].decode("utf-8", errors="strict")


def enrich_tokens(addresses: set[str], network: NetworkConfig) -> list[TokenMetadata]:
    """Best-effort ERC-20 metadata (symbol, decimals) for the given contract addresses.

    Reads via `network.rpc_url` (eth_call to `symbol()`/`decimals()`), giving the
    LLM the on-chain context to say "12.5 USDC" instead of a raw wei amount.
    A token that fails to resolve (bad RPC, non-standard ABI e.g. bytes32 symbol)
    is skipped, not fatal: graceful degradation, not a 502 for the whole request.
    """
    if not addresses:
        return []

    tokens = []
    with RPCClient(network.rpc_url) as client:
        for address in sorted(addresses):
            symbol: str | None = None
            decimals: int | None = None
            try:
                symbol = _decode_string(client.eth_call(address, _SYMBOL_SELECTOR))
            except (RPCError, ValueError, UnicodeDecodeError):
                logger.warning("token_symbol_unavailable", extra={"address": address})
            try:
                decimals = _decode_uint(client.eth_call(address, _DECIMALS_SELECTOR))
            except (RPCError, ValueError):
                logger.warning("token_decimals_unavailable", extra={"address": address})
            tokens.append(TokenMetadata(address=address, symbol=symbol, decimals=decimals))
    return tokens
