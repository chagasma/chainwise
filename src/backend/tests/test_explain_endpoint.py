from typing import Any

import chainwise.api.routes as routes_module
import pytest
from chainwise.adapters import TransactionNotFoundError
from chainwise.api.routes import get_graph
from chainwise.main import app
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

client = TestClient(app)

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
    "decoded_input": None,
    "revert_reason": None,
}


class _FakeBlockscoutClient:
    def __call__(self, *_args: Any, **_kwargs: Any) -> "_FakeBlockscoutClient":
        return self

    def __enter__(self) -> "_FakeBlockscoutClient":
        return self

    def __exit__(self, *_exc: Any) -> None:
        return None

    def get_transaction(self, _tx_hash: str) -> dict[str, Any]:
        return TX

    def get_transaction_logs(self, _tx_hash: str) -> list[dict[str, Any]]:
        return []


class _NotFoundBlockscoutClient(_FakeBlockscoutClient):
    def get_transaction(self, tx_hash: str) -> dict[str, Any]:
        raise TransactionNotFoundError(tx_hash)


class _FakeGraph:
    def __init__(self, response: str) -> None:
        self._response = response
        self.invoke_calls = 0

    def invoke(self, _state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        self.invoke_calls += 1
        return {"messages": [AIMessage(content=self._response)]}


class _BrokenGraph:
    def invoke(self, _state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("OpenRouter unreachable")


@pytest.fixture
def override_graph():
    def _override(graph: Any) -> None:
        app.dependency_overrides[get_graph] = lambda: graph

    yield _override
    app.dependency_overrides.pop(get_graph, None)


def test_explain_transaction_returns_grounded_explanation(
    monkeypatch: Any, override_graph: Any
) -> None:
    monkeypatch.setattr(routes_module, "BlockscoutClient", _FakeBlockscoutClient())
    override_graph(_FakeGraph("This transfer moved 1000 wei from 0xfrom to 0xto."))

    response = client.get("/tx/0xabc/explain")

    assert response.status_code == 200
    body = response.json()
    assert body["explanation"] == "This transfer moved 1000 wei from 0xfrom to 0xto."
    assert body["summary"]["hash"] == "0xabc"
    assert body["thread_id"] == "0xabc"


def test_explain_transaction_returns_502_when_llm_fails(
    monkeypatch: Any, override_graph: Any
) -> None:
    monkeypatch.setattr(routes_module, "BlockscoutClient", _FakeBlockscoutClient())
    override_graph(_BrokenGraph())

    response = client.get("/tx/0xabc/explain")

    assert response.status_code == 502
    assert "LLM explanation unavailable" in response.json()["detail"]


def test_explain_transaction_returns_404_without_calling_graph(
    monkeypatch: Any, override_graph: Any
) -> None:
    monkeypatch.setattr(routes_module, "BlockscoutClient", _NotFoundBlockscoutClient())
    graph = _FakeGraph("should never be used")
    override_graph(graph)

    response = client.get("/tx/0xdoesnotexist/explain")

    assert response.status_code == 404
    assert graph.invoke_calls == 0
