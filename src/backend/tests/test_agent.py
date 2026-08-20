from typing import Any

import chainwise.agent.graph as graph_module
from chainwise.agent.graph import build_graph
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver


class _FakeLLM:
    def invoke(self, _messages: list[Any]) -> AIMessage:
        return AIMessage(content="This transaction transferred 10 tokens.")


def test_build_graph_runs_explain_node(monkeypatch: Any) -> None:
    monkeypatch.setattr(graph_module, "get_llm", lambda: _FakeLLM())

    graph = build_graph(checkpointer=InMemorySaver())
    result = graph.invoke(
        {
            "messages": [HumanMessage(content='{"hash": "0xabc"}')],
            "reverted": False,
        },
        config={"configurable": {"thread_id": "0xabc"}},
    )

    assert result["messages"][-1].content == "This transaction transferred 10 tokens."


def test_build_graph_routes_reverted_tx_to_diagnose_node(monkeypatch: Any) -> None:
    calls: list[list[Any]] = []

    class _RecordingLLM:
        def invoke(self, messages: list[Any]) -> AIMessage:
            calls.append(messages)
            return AIMessage(content="Likely root cause: insufficient balance.")

    monkeypatch.setattr(graph_module, "get_llm", lambda: _RecordingLLM())

    graph = build_graph(checkpointer=InMemorySaver())
    result = graph.invoke(
        {
            "messages": [HumanMessage(content='{"hash": "0xabc"}')],
            "reverted": True,
        },
        config={"configurable": {"thread_id": "0xreverted"}},
    )

    assert result["messages"][-1].content == "Likely root cause: insufficient balance."
    assert "diagnos" in calls[0][0].content.lower()


def test_build_graph_routes_undecoded_tx_to_clarify_node(monkeypatch: Any) -> None:
    calls: list[list[Any]] = []

    class _RecordingLLM:
        def invoke(self, messages: list[Any]) -> AIMessage:
            calls.append(messages)
            return AIMessage(content="What ABI or repo should I check?")

    monkeypatch.setattr(graph_module, "get_llm", lambda: _RecordingLLM())

    graph = build_graph(checkpointer=InMemorySaver())
    result = graph.invoke(
        {
            "messages": [HumanMessage(content='{"hash": "0xabc"}')],
            "reverted": False,
            "undecoded": True,
        },
        config={"configurable": {"thread_id": "0xundecoded"}},
    )

    assert result["messages"][-1].content == "What ABI or repo should I check?"
    assert "clarifying question" in calls[0][0].content.lower()


def test_build_graph_prefers_diagnose_over_clarify_when_both_apply(monkeypatch: Any) -> None:
    calls: list[list[Any]] = []

    class _RecordingLLM:
        def invoke(self, messages: list[Any]) -> AIMessage:
            calls.append(messages)
            return AIMessage(content="diagnosed")

    monkeypatch.setattr(graph_module, "get_llm", lambda: _RecordingLLM())

    graph = build_graph(checkpointer=InMemorySaver())
    graph.invoke(
        {
            "messages": [HumanMessage(content='{"hash": "0xabc"}')],
            "reverted": True,
            "undecoded": True,
        },
        config={"configurable": {"thread_id": "0xboth"}},
    )

    assert "diagnos" in calls[0][0].content.lower()


def test_build_graph_appends_mode_addendum_to_system_prompt(monkeypatch: Any) -> None:
    calls: list[list[Any]] = []

    class _RecordingLLM:
        def invoke(self, messages: list[Any]) -> AIMessage:
            calls.append(messages)
            return AIMessage(content="explained for support")

    monkeypatch.setattr(graph_module, "get_llm", lambda: _RecordingLLM())

    graph = build_graph(checkpointer=InMemorySaver())
    graph.invoke(
        {
            "messages": [HumanMessage(content='{"hash": "0xabc"}')],
            "reverted": False,
            "mode": "support",
        },
        config={"configurable": {"thread_id": "0xabc:support"}},
    )

    system_prompt = calls[0][0].content
    assert "non-technical end user" in system_prompt


def test_build_graph_defaults_to_developer_mode_when_unset(monkeypatch: Any) -> None:
    calls: list[list[Any]] = []

    class _RecordingLLM:
        def invoke(self, messages: list[Any]) -> AIMessage:
            calls.append(messages)
            return AIMessage(content="explained")

    monkeypatch.setattr(graph_module, "get_llm", lambda: _RecordingLLM())

    graph = build_graph(checkpointer=InMemorySaver())
    graph.invoke(
        {"messages": [HumanMessage(content='{"hash": "0xabc"}')], "reverted": False},
        config={"configurable": {"thread_id": "0xabc"}},
    )

    system_prompt = calls[0][0].content
    assert "non-technical end user" not in system_prompt
    assert "security auditor" not in system_prompt


def test_build_graph_appends_gas_tips_addendum_when_requested(monkeypatch: Any) -> None:
    calls: list[list[Any]] = []

    class _RecordingLLM:
        def invoke(self, messages: list[Any]) -> AIMessage:
            calls.append(messages)
            return AIMessage(content="explained with gas tips")

    monkeypatch.setattr(graph_module, "get_llm", lambda: _RecordingLLM())

    graph = build_graph(checkpointer=InMemorySaver())
    graph.invoke(
        {
            "messages": [HumanMessage(content='{"hash": "0xabc"}')],
            "reverted": False,
            "gas_tips": True,
        },
        config={"configurable": {"thread_id": "0xabc:gas"}},
    )

    assert "Gas efficiency" in calls[0][0].content


def test_build_graph_omits_gas_tips_addendum_by_default(monkeypatch: Any) -> None:
    calls: list[list[Any]] = []

    class _RecordingLLM:
        def invoke(self, messages: list[Any]) -> AIMessage:
            calls.append(messages)
            return AIMessage(content="explained")

    monkeypatch.setattr(graph_module, "get_llm", lambda: _RecordingLLM())

    graph = build_graph(checkpointer=InMemorySaver())
    graph.invoke(
        {"messages": [HumanMessage(content='{"hash": "0xabc"}')], "reverted": False},
        config={"configurable": {"thread_id": "0xabc"}},
    )

    assert "Gas efficiency" not in calls[0][0].content


def test_build_graph_combines_mode_and_gas_tips_addenda(monkeypatch: Any) -> None:
    calls: list[list[Any]] = []

    class _RecordingLLM:
        def invoke(self, messages: list[Any]) -> AIMessage:
            calls.append(messages)
            return AIMessage(content="explained for an auditor with gas tips")

    monkeypatch.setattr(graph_module, "get_llm", lambda: _RecordingLLM())

    graph = build_graph(checkpointer=InMemorySaver())
    graph.invoke(
        {
            "messages": [HumanMessage(content='{"hash": "0xabc"}')],
            "reverted": False,
            "mode": "auditor",
            "gas_tips": True,
        },
        config={"configurable": {"thread_id": "0xabc:auditor:gas"}},
    )

    system_prompt = calls[0][0].content
    assert "security auditor" in system_prompt
    assert "Gas efficiency" in system_prompt


def test_build_graph_persists_state_across_calls_with_same_thread(monkeypatch: Any) -> None:
    monkeypatch.setattr(graph_module, "get_llm", lambda: _FakeLLM())
    checkpointer = InMemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config: RunnableConfig = {"configurable": {"thread_id": "0xabc"}}

    graph.invoke({"messages": [HumanMessage(content="explain")]}, config=config)
    state = graph.get_state(config)

    assert len(state.values["messages"]) == 2  # human + ai
