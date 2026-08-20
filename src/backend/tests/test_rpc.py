import json

import httpx
import pytest
from chainwise.adapters import RPCClient, RPCError

CONTRACT = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def _client(handler: httpx.MockTransport) -> RPCClient:
    return RPCClient("https://rpc.example", transport=handler)


def test_eth_call_returns_raw_result() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": "0x06"})
    )

    with _client(transport) as client:
        assert client.eth_call(CONTRACT, "0x313ce567") == "0x06"


def test_eth_call_raises_on_jsonrpc_error() -> None:
    error_body = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32000, "message": "execution reverted"},
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=error_body))

    with _client(transport) as client, pytest.raises(RPCError, match="execution reverted"):
        client.eth_call(CONTRACT, "0xdeadbeef")


def test_eth_call_raises_on_http_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(503, json={}))

    with _client(transport) as client, pytest.raises(RPCError):
        client.eth_call(CONTRACT, "0xdeadbeef")


def test_eth_call_raises_on_connection_failure() -> None:
    def raise_connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    transport = httpx.MockTransport(raise_connect_error)

    with _client(transport) as client, pytest.raises(RPCError):
        client.eth_call(CONTRACT, "0xdeadbeef")


def test_request_id_increments_across_calls() -> None:
    seen_ids: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_ids.append(json.loads(request.content)["id"])
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": seen_ids[-1], "result": "0x0"})

    transport = httpx.MockTransport(handler)

    with _client(transport) as client:
        client.eth_call(CONTRACT, "0x1")
        client.eth_call(CONTRACT, "0x2")

    assert seen_ids == [1, 2]
