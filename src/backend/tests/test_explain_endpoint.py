from typing import Any

import chainwise.api.routes as routes_module
import pytest
from chainwise.adapters import TransactionNotFoundError
from chainwise.api.routes import get_graph
from chainwise.main import app
from chainwise.models import DecodedCall, RepoGroundingResult
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
        self.last_state: dict[str, Any] | None = None
        self.last_config: dict[str, Any] | None = None

    def invoke(self, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        self.invoke_calls += 1
        self.last_state = state
        self.last_config = config
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
    assert body["mode"] == "developer"
    assert body["gas_tips"] is False


def test_explain_transaction_defaults_to_developer_mode(
    monkeypatch: Any, override_graph: Any
) -> None:
    monkeypatch.setattr(routes_module, "BlockscoutClient", _FakeBlockscoutClient())
    graph = _FakeGraph("explained")
    override_graph(graph)

    client.get("/tx/0xabc/explain")

    assert graph.last_state is not None
    assert graph.last_state["mode"] == "developer"


def test_explain_transaction_passes_mode_and_isolates_thread_id(
    monkeypatch: Any, override_graph: Any
) -> None:
    monkeypatch.setattr(routes_module, "BlockscoutClient", _FakeBlockscoutClient())
    graph = _FakeGraph("explained for an auditor")
    override_graph(graph)

    response = client.get("/tx/0xabc/explain?mode=auditor")

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "auditor"
    assert body["thread_id"] == "0xabc:auditor"
    assert graph.last_state is not None
    assert graph.last_state["mode"] == "auditor"
    assert graph.last_config is not None
    assert graph.last_config["configurable"]["thread_id"] == "0xabc:auditor"


def test_explain_transaction_passes_gas_tips_and_isolates_thread_id(
    monkeypatch: Any, override_graph: Any
) -> None:
    monkeypatch.setattr(routes_module, "BlockscoutClient", _FakeBlockscoutClient())
    graph = _FakeGraph("explained with gas tips")
    override_graph(graph)

    response = client.get("/tx/0xabc/explain?gas_tips=true")

    assert response.status_code == 200
    body = response.json()
    assert body["gas_tips"] is True
    assert body["thread_id"] == "0xabc:gas"
    assert graph.last_state is not None
    assert graph.last_state["gas_tips"] is True


def test_explain_transaction_combines_mode_and_gas_tips_in_thread_id(
    monkeypatch: Any, override_graph: Any
) -> None:
    monkeypatch.setattr(routes_module, "BlockscoutClient", _FakeBlockscoutClient())
    graph = _FakeGraph("explained for an auditor with gas tips")
    override_graph(graph)

    response = client.get("/tx/0xabc/explain?mode=auditor&gas_tips=true")

    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == "0xabc:auditor:gas"


def test_explain_transaction_rejects_unknown_mode(
    monkeypatch: Any, override_graph: Any
) -> None:
    monkeypatch.setattr(routes_module, "BlockscoutClient", _FakeBlockscoutClient())
    override_graph(_FakeGraph("should never be used"))

    response = client.get("/tx/0xabc/explain?mode=hacker")

    assert response.status_code == 422


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


def test_explain_transaction_includes_repo_grounding_when_found(
    monkeypatch: Any, override_graph: Any
) -> None:
    monkeypatch.setattr(routes_module, "BlockscoutClient", _FakeBlockscoutClient())
    override_graph(_FakeGraph("Decoded via the repo's ABI."))
    grounding = RepoGroundingResult(
        repo="example/contracts",
        file_path="abi/Token.json",
        source_url="https://github.com/example/contracts/blob/HEAD/abi/Token.json",
        decoded_call=DecodedCall(
            function="transfer",
            signature="transfer(address,uint256)",
            parameters={"to": "0xto", "value": "1000"},
        ),
    )
    monkeypatch.setattr(routes_module, "ground_transaction", lambda *_args, **_kwargs: grounding)

    response = client.get("/tx/0xabc/explain")

    assert response.status_code == 200
    body = response.json()
    assert body["grounding"]["repo"] == "example/contracts"
    assert body["grounding"]["decoded_call"]["function"] == "transfer"


def test_explain_transaction_skips_grounding_when_explorer_already_decoded(
    monkeypatch: Any, override_graph: Any
) -> None:
    """decoded_input is non-null in the fixture below -> repo grounding must not be attempted."""

    class _DecodedBlockscoutClient(_FakeBlockscoutClient):
        def get_transaction(self, _tx_hash: str) -> dict[str, Any]:
            return {**TX, "decoded_input": {"method_call": "transfer(address,uint256)"}}

    monkeypatch.setattr(routes_module, "BlockscoutClient", _DecodedBlockscoutClient())
    override_graph(_FakeGraph("Explained from the explorer's own ABI."))

    def _fail_if_called(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("ground_transaction should not be called when decoded_input is set")

    monkeypatch.setattr(routes_module, "ground_transaction", _fail_if_called)

    response = client.get("/tx/0xabc/explain")

    assert response.status_code == 200
    assert response.json()["grounding"] is None


def test_explain_transaction_includes_security_findings_from_decoded_input(
    monkeypatch: Any, override_graph: Any
) -> None:
    class _RiskyBlockscoutClient(_FakeBlockscoutClient):
        def get_transaction(self, _tx_hash: str) -> dict[str, Any]:
            return {
                **TX,
                "decoded_input": {
                    "method_call": "transferOwnership(address newOwner)",
                    "parameters": [{"name": "newOwner", "type": "address", "value": "0xnew"}],
                },
            }

    monkeypatch.setattr(routes_module, "BlockscoutClient", _RiskyBlockscoutClient())
    override_graph(_FakeGraph("This transfers contract ownership."))

    response = client.get("/tx/0xabc/explain")

    assert response.status_code == 200
    findings = response.json()["security_findings"]
    assert len(findings) == 1
    assert findings[0]["pattern"] == "transferownership"
    assert findings[0]["severity"] == "high"


def test_explain_transaction_returns_no_security_findings_for_ordinary_call(
    monkeypatch: Any, override_graph: Any
) -> None:
    monkeypatch.setattr(routes_module, "BlockscoutClient", _FakeBlockscoutClient())
    override_graph(_FakeGraph("This transfers tokens."))

    response = client.get("/tx/0xabc/explain")

    assert response.status_code == 200
    assert response.json()["security_findings"] == []
