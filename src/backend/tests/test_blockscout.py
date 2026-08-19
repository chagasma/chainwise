import httpx
import pytest
from chainwise.adapters import BlockscoutClient, BlockscoutError, TransactionNotFoundError

TX_HASH = "0xabc123"

TX_PAYLOAD = {
    "hash": TX_HASH,
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


def _client(handler: httpx.MockTransport) -> BlockscoutClient:
    return BlockscoutClient("https://explorer.example", transport=handler)


def test_get_transaction_returns_parsed_json() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=TX_PAYLOAD))

    with _client(transport) as client:
        assert client.get_transaction(TX_HASH) == TX_PAYLOAD


def test_get_transaction_logs_returns_items() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"items": [{"a": 1}]}))

    with _client(transport) as client:
        assert client.get_transaction_logs(TX_HASH) == [{"a": 1}]


def test_get_transaction_raises_not_found_on_404() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(404, json={}))

    with _client(transport) as client, pytest.raises(TransactionNotFoundError):
        client.get_transaction(TX_HASH)


def test_get_transaction_raises_blockscout_error_on_5xx() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(503, json={}))

    with _client(transport) as client, pytest.raises(BlockscoutError):
        client.get_transaction(TX_HASH)


def test_get_transaction_raises_blockscout_error_on_connection_failure() -> None:
    def raise_connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    transport = httpx.MockTransport(raise_connect_error)

    with _client(transport) as client, pytest.raises(BlockscoutError):
        client.get_transaction(TX_HASH)
