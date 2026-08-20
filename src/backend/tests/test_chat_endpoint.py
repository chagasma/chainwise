from typing import Any

import pytest
from chainwise.api.routes import get_graph
from chainwise.main import app
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

client = TestClient(app)


class _StateSnapshot:
    def __init__(self, values: dict[str, Any]) -> None:
        self.values = values


class _FakeGraph:
    """Mimics an already-checkpointed thread: `get_state` returns prior
    messages, `invoke` records the call and returns a canned reply."""

    def __init__(self, reply: str, existing_messages: list[Any] | None = None) -> None:
        self._reply = reply
        self._existing_messages = existing_messages or []
        self.invoke_calls = 0
        self.last_state: dict[str, Any] | None = None
        self.last_config: dict[str, Any] | None = None

    def get_state(self, _config: dict[str, Any]) -> _StateSnapshot:
        return _StateSnapshot({"messages": self._existing_messages})

    def invoke(self, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        self.invoke_calls += 1
        self.last_state = state
        self.last_config = config
        return {"messages": [AIMessage(content=self._reply)]}


@pytest.fixture
def override_graph():
    def _override(graph: Any) -> None:
        app.dependency_overrides[get_graph] = lambda: graph

    yield _override
    app.dependency_overrides.pop(get_graph, None)


def test_chat_continues_an_existing_thread(override_graph: Any) -> None:
    graph = _FakeGraph(
        "It sent 500 USDC.",
        existing_messages=[HumanMessage(content="{}"), AIMessage(content="explained")],
    )
    override_graph(graph)

    response = client.post("/chat", json={"thread_id": "0xabc", "message": "how much was sent?"})

    assert response.status_code == 200
    body = response.json()
    assert body == {"reply": "It sent 500 USDC.", "thread_id": "0xabc"}
    assert graph.last_config is not None
    assert graph.last_config["configurable"]["thread_id"] == "0xabc"
    assert graph.last_state is not None
    assert graph.last_state["messages"][0].content == "how much was sent?"


def test_chat_rejects_unknown_thread(override_graph: Any) -> None:
    graph = _FakeGraph("should not be reached", existing_messages=[])
    override_graph(graph)

    response = client.post("/chat", json={"thread_id": "0xnope", "message": "hi"})

    assert response.status_code == 404
    assert graph.invoke_calls == 0
