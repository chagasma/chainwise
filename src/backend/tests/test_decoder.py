from chainwise.services.decoder import (
    _canonical_signature,
    decode_function_input,
    find_function_abi,
    function_selector,
)
from eth_abi.abi import encode as abi_encode
from eth_utils.crypto import keccak

TRANSFER_ABI = {
    "type": "function",
    "name": "transfer",
    "inputs": [
        {"name": "to", "type": "address"},
        {"name": "value", "type": "uint256"},
    ],
    "outputs": [{"type": "bool"}],
    "stateMutability": "nonpayable",
}

APPROVE_ABI = {
    "type": "function",
    "name": "approve",
    "inputs": [
        {"name": "spender", "type": "address"},
        {"name": "value", "type": "uint256"},
    ],
    "stateMutability": "nonpayable",
}

# A struct-taking function, to exercise tuple canonicalization.
SWAP_ABI = {
    "type": "function",
    "name": "swap",
    "inputs": [
        {
            "name": "params",
            "type": "tuple",
            "components": [
                {"name": "tokenIn", "type": "address"},
                {"name": "amountIn", "type": "uint256"},
            ],
        },
        {
            "name": "recipients",
            "type": "tuple[]",
            "components": [{"name": "addr", "type": "address"}],
        },
    ],
}

ABI = [TRANSFER_ABI, APPROVE_ABI, SWAP_ABI, {"type": "event", "name": "Transfer", "inputs": []}]

TO = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
AMOUNT = 12_500_000_000_000_000_000  # 12.5 * 1e18


def _transfer_calldata() -> str:
    selector = function_selector("transfer(address,uint256)")
    encoded = abi_encode(["address", "uint256"], [TO, AMOUNT]).hex()
    return selector + encoded


def test_function_selector_matches_known_erc20_transfer() -> None:
    assert function_selector("transfer(address,uint256)") == "0xa9059cbb"


def test_canonical_signature_expands_tuple_and_tuple_array() -> None:
    assert _canonical_signature(SWAP_ABI) == "swap((address,uint256),(address)[])"


def test_canonical_signature_selector_matches_manual_keccak() -> None:
    signature = _canonical_signature(SWAP_ABI)
    expected = "0x" + keccak(text=signature)[:4].hex()
    assert function_selector(signature) == expected


def test_find_function_abi_matches_by_selector() -> None:
    entry = find_function_abi(ABI, "0xa9059cbb")
    assert entry is not None
    assert entry["name"] == "transfer"


def test_find_function_abi_ignores_non_function_entries() -> None:
    # The Transfer *event* has the same name but is not a function; must not match.
    assert find_function_abi(ABI, "0x00000000") is None


def test_find_function_abi_returns_none_when_no_match() -> None:
    assert find_function_abi(ABI, "0xdeadbeef") is None


def test_decode_function_input_returns_named_parameters() -> None:
    decoded = decode_function_input(_transfer_calldata(), ABI)

    assert decoded is not None
    assert decoded.function == "transfer"
    assert decoded.signature == "transfer(address,uint256)"
    assert decoded.parameters == {"to": TO, "value": str(AMOUNT)}


def test_decode_function_input_stringifies_large_ints() -> None:
    """uint256 values must survive JSON round-tripping without precision loss."""
    decoded = decode_function_input(_transfer_calldata(), ABI)
    assert decoded is not None
    assert isinstance(decoded.parameters["value"], str)


def test_decode_function_input_returns_none_for_unmatched_selector() -> None:
    calldata = "0xffffffff" + "00" * 64
    assert decode_function_input(calldata, ABI) is None


def test_decode_function_input_returns_none_for_short_calldata() -> None:
    assert decode_function_input("0xab", ABI) is None


def test_decode_function_input_returns_none_for_truncated_arguments() -> None:
    # Matches the transfer() selector but the encoded arguments are cut short.
    selector = function_selector("transfer(address,uint256)")
    assert decode_function_input(selector + "00" * 10, ABI) is None
