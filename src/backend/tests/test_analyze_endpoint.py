from typing import Any

import chainwise.api.routes as routes_module
import pytest
from chainwise.api.routes import get_graph
from chainwise.main import app
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

client = TestClient(app)

TX_TEMPLATE = {
    "status": "ok",
    "timestamp": "2026-01-01T00:00:00.000000Z",
    "value": "1000",
    "gas_used": "21000",
    "fee": {"value": "42"},
    "method": "transfer",
    "decoded_input": None,
    "revert_reason": None,
}


class _MultiTxBlockscoutClient:
    """Returns a distinct tx per hash, keyed by a small fixture map, so the
    hashes requested actually come back distinguishable in the response."""

    def __init__(self, txs: dict[str, dict[str, Any]]) -> None:
        self._txs = txs

    def __call__(self, *_args: Any, **_kwargs: Any) -> "_MultiTxBlockscoutClient":
        return self

    def __enter__(self) -> "_MultiTxBlockscoutClient":
        return self

    def __exit__(self, *_exc: Any) -> None:
        return None

    def get_transaction(self, tx_hash: str) -> dict[str, Any]:
        return self._txs[tx_hash]

    def get_transaction_logs(self, _tx_hash: str) -> list[dict[str, Any]]:
        return []


class _FakeGraph:
    def __init__(self, response: str) -> None:
        self.last_state: dict[str, Any] | None = None
        self.last_config: dict[str, Any] | None = None
        self._response = response

    def invoke(self, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        self.last_state = state
        self.last_config = config
        return {"messages": [AIMessage(content=self._response)]}


@pytest.fixture
def override_graph():
    def _override(graph: Any) -> None:
        app.dependency_overrides[get_graph] = lambda: graph

    yield _override
    app.dependency_overrides.pop(get_graph, None)


def test_analyze_transactions_requires_at_least_two_hashes(
    monkeypatch: Any, override_graph: Any
) -> None:
    override_graph(_FakeGraph("should never be used"))

    response = client.get("/analyze?hash=0x1")

    assert response.status_code == 400


def test_analyze_transactions_dedupes_hashes_before_requiring_two(
    monkeypatch: Any, override_graph: Any
) -> None:
    override_graph(_FakeGraph("should never be used"))

    response = client.get("/analyze?hash=0x1&hash=0x1")

    assert response.status_code == 400


def test_analyze_transactions_returns_combined_explanation_and_relations(
    monkeypatch: Any, override_graph: Any
) -> None:
    txs = {
        "0x1": {
            **TX_TEMPLATE,
            "hash": "0x1",
            "block_number": 200,
            "from": {"hash": "0xshared"},
            "to": {"hash": "0xcontractA"},
        },
        "0x2": {
            **TX_TEMPLATE,
            "hash": "0x2",
            "block_number": 100,
            "from": {"hash": "0xshared"},
            "to": {"hash": "0xcontractB"},
        },
    }
    monkeypatch.setattr(routes_module, "BlockscoutClient", _MultiTxBlockscoutClient(txs))
    graph = _FakeGraph("These two transactions share a sender.")
    override_graph(graph)

    response = client.get("/analyze?hash=0x1&hash=0x2")

    assert response.status_code == 200
    body = response.json()
    assert body["explanation"] == "These two transactions share a sender."
    assert body["mode"] == "developer"
    # sorted chronologically by block_number: 0x2 (100) before 0x1 (200)
    assert [t["summary"]["hash"] for t in body["transactions"]] == ["0x2", "0x1"]
    assert len(body["relations"]) == 1
    assert body["relations"][0]["kind"] == "shared_sender"
    assert graph.last_state is not None
    assert graph.last_state["multi"] is True


def test_analyze_transactions_passes_mode_and_isolates_thread_id(
    monkeypatch: Any, override_graph: Any
) -> None:
    txs = {
        "0x1": {**TX_TEMPLATE, "hash": "0x1", "block_number": 100, "from": {"hash": "0xa"}},
        "0x2": {**TX_TEMPLATE, "hash": "0x2", "block_number": 200, "from": {"hash": "0xb"}},
    }
    monkeypatch.setattr(routes_module, "BlockscoutClient", _MultiTxBlockscoutClient(txs))
    graph = _FakeGraph("explained for an auditor")
    override_graph(graph)

    response = client.get("/analyze?hash=0x1&hash=0x2&mode=auditor")

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "auditor"
    assert body["thread_id"] == "multi:0x1+0x2:auditor"
