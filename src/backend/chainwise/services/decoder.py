from typing import Any

from eth_abi.abi import decode as abi_decode
from eth_utils.crypto import keccak

from chainwise.models import DecodedCall


def function_selector(signature: str) -> str:
    """The 4-byte selector Solidity computes for a canonical function signature."""
    return "0x" + keccak(text=signature)[:4].hex()


def _canonical_type(param: dict[str, Any]) -> str:
    """Resolves an ABI parameter's canonical type, recursing into tuples.
    Solidity's signature for a struct needs the expanded component list
    ("(uint256,address)"), not the literal word "tuple" the JSON ABI uses."""
    param_type: str = param["type"]
    if not param_type.startswith("tuple"):
        return param_type
    components = ",".join(_canonical_type(c) for c in param["components"])
    array_suffix = param_type.removeprefix("tuple")
    return f"({components}){array_suffix}"


def _canonical_signature(entry: dict[str, Any]) -> str:
    types = ",".join(_canonical_type(p) for p in entry.get("inputs", []))
    return f"{entry['name']}({types})"


def find_function_abi(abi: list[dict[str, Any]], selector: str) -> dict[str, Any] | None:
    """Finds the ABI entry whose computed selector matches `selector` (e.g. "0xa9059cbb")."""
    for entry in abi:
        if entry.get("type") != "function":
            continue
        try:
            if function_selector(_canonical_signature(entry)) == selector:
                return entry
        except KeyError:
            continue
    return None


def _jsonify(value: Any) -> Any:
    """Stringifies ints (uint256 loses precision as a JSON number) and
    hex-encodes bytes, mirroring TransactionSummary.value_wei."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, bytes):
        return "0x" + value.hex()
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    return value


def decode_function_input(input_data: str, abi: list[dict[str, Any]]) -> DecodedCall | None:
    """Decodes `input_data` (0x-prefixed calldata) against the first matching
    ABI entry. Returns None on no match rather than raising — an unmatched
    artifact isn't an error, it's just not the right one."""
    data = bytes.fromhex(input_data.removeprefix("0x"))
    if len(data) < 4:
        return None
    entry = find_function_abi(abi, "0x" + data[:4].hex())
    if entry is None:
        return None

    inputs = entry.get("inputs", [])
    types = [_canonical_type(p) for p in inputs]
    try:
        values = abi_decode(types, data[4:]) if types else ()
    except Exception:
        # eth_abi raises several distinct internal error types for malformed
        # calldata (wrong length, invalid pointer, ...) — any of them just
        # means "not a match", same as find_function_abi returning None above.
        return None

    parameters = {
        (param.get("name") or f"arg{i}"): _jsonify(value)
        for i, (param, value) in enumerate(zip(inputs, values, strict=True))
    }
    return DecodedCall(
        function=entry["name"], signature=_canonical_signature(entry), parameters=parameters
    )
