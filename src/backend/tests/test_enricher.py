import json

import httpx
from chainwise.adapters import RPCClient
from chainwise.config import NetworkConfig
from chainwise.services.enricher import enrich_tokens

USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
BAD_TOKEN = "0xbadbad0000000000000000000000000000bad0"

NETWORK = NetworkConfig(
    name="test",
    chain_id=1,
    explorer_url="https://explorer.example",
    rpc_url="https://rpc.example",
    repos=[],
)

def _abi_encode_string(value: str) -> str:
    """Builds the ABI encoding a real eth_call would return for `symbol() -> string`."""
    raw = value.encode()
    padded = raw + b"\x00" * (-len(raw) % 32)
    offset = (32).to_bytes(32, "big")
    length = len(raw).to_bytes(32, "big")
    return "0x" + (offset + length + padded).hex()


_SYMBOL_RESULT = _abi_encode_string("USDC")
_DECIMALS_RESULT = "0x" + (6).to_bytes(32, "big").hex()


def _handler(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content)
    to = payload["params"][0]["to"]
    data = payload["params"][0]["data"]
    if to == BAD_TOKEN:
        return httpx.Response(
            200, json={"jsonrpc": "2.0", "id": payload["id"], "error": {"message": "revert"}}
        )
    result = _SYMBOL_RESULT if data == "0x95d89b41" else _DECIMALS_RESULT
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result})


def test_enrich_tokens_decodes_symbol_and_decimals(monkeypatch) -> None:
    transport = httpx.MockTransport(_handler)
    monkeypatch.setattr(
        "chainwise.services.enricher.RPCClient",
        lambda rpc_url: RPCClient(rpc_url, transport=transport),
    )

    tokens = enrich_tokens({USDC}, NETWORK)

    assert len(tokens) == 1
    assert tokens[0].address == USDC
    assert tokens[0].symbol == "USDC"
    assert tokens[0].decimals == 6


def test_enrich_tokens_degrades_gracefully_on_rpc_error(monkeypatch) -> None:
    transport = httpx.MockTransport(_handler)
    monkeypatch.setattr(
        "chainwise.services.enricher.RPCClient",
        lambda rpc_url: RPCClient(rpc_url, transport=transport),
    )

    tokens = enrich_tokens({BAD_TOKEN}, NETWORK)

    assert len(tokens) == 1
    assert tokens[0].symbol is None
    assert tokens[0].decimals is None


def test_enrich_tokens_returns_empty_for_no_addresses() -> None:
    assert enrich_tokens(set(), NETWORK) == []
