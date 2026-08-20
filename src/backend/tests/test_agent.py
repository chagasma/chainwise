from typing import Any

import chainwise.agent.graph as graph_module
from chainwise.agent.graph import build_graph
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
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
            "messages": [
                SystemMessage(content="You explain transactions."),
                HumanMessage(content='{"hash": "0xabc"}'),
            ]
        },
        config={"configurable": {"thread_id": "0xabc"}},
    )

    assert result["messages"][-1].content == "This transaction transferred 10 tokens."


def test_build_graph_persists_state_across_calls_with_same_thread(monkeypatch: Any) -> None:
    monkeypatch.setattr(graph_module, "get_llm", lambda: _FakeLLM())
    checkpointer = InMemorySaver()
    graph = build_graph(checkpointer=checkpointer)
    config: RunnableConfig = {"configurable": {"thread_id": "0xabc"}}

    graph.invoke({"messages": [HumanMessage(content="explain")]}, config=config)
    state = graph.get_state(config)

    assert len(state.values["messages"]) == 2  # human + ai
