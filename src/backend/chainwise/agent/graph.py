from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph

from chainwise.agent.llm import get_llm


def _explain(state: MessagesState) -> dict[str, Any]:
    llm = get_llm()
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def build_graph(checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """One-node graph: given messages (system prompt + tx context), ask the LLM to explain.

    Intentionally a straight line today. The triage-flow and mode-switching bonus
    features are where branching actually belongs, so this node becomes one step
    inside a larger graph then rather than growing conditional edges it doesn't need yet.
    """
    graph = StateGraph(MessagesState)
    graph.add_node("explain", _explain)
    graph.add_edge(START, "explain")
    graph.add_edge("explain", END)
    return graph.compile(checkpointer=checkpointer)
