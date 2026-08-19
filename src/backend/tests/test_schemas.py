from chainwise.api.schemas import TransactionSummary

TX = {
    "hash": "0xabc",
    "status": "ok",
    "block_number": 100,
    "timestamp": "2026-01-01T00:00:00.000000Z",
    "from": {"hash": "0xfrom"},
    "to": {"hash": "0xto"},
    "value": "1000",
    "gas_used": "21000",
    "fee": {"value": "42"},
    "method": "transfer",
    "decoded_input": {"method_call": "transfer(address,uint256)"},
    "revert_reason": None,
}

LOGS = [
    {
        "address": {"hash": "0xtoken"},
        "decoded": {"method_call": "Transfer(address,address,uint256)"},
    }
]


def test_from_blockscout_maps_success_status() -> None:
    summary = TransactionSummary.from_blockscout(TX, LOGS, "https://explorer.example")

    assert summary.status == "success"
    assert summary.from_address == "0xfrom"
    assert summary.to_address == "0xto"
    assert summary.logs[0].event == "Transfer(address,address,uint256)"
    assert summary.source_url == "https://explorer.example/tx/0xabc"


def test_from_blockscout_maps_reverted_status() -> None:
    reverted = {**TX, "status": "error", "revert_reason": "insufficient balance"}

    summary = TransactionSummary.from_blockscout(reverted, [], "https://explorer.example")

    assert summary.status == "reverted"
    assert summary.revert_reason == "insufficient balance"


def test_from_blockscout_handles_contract_creation_without_to() -> None:
    no_to = {**TX, "to": None}

    summary = TransactionSummary.from_blockscout(no_to, [], "https://explorer.example")

    assert summary.to_address is None
