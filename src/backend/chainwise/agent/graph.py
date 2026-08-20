from functools import partial
from typing import Any

from langchain_core.messages import SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph

from chainwise.agent.llm import get_llm
from chainwise.agent.prompts import (
    DIAGNOSE_SYSTEM_PROMPT,
    EXPLAIN_SYSTEM_PROMPT,
    GAS_TIPS_ADDENDUM,
    MODE_ADDENDA,
)
from chainwise.models import DEFAULT_MODE, ExplanationMode


class ExplainState(MessagesState):
    reverted: bool
    mode: ExplanationMode
    gas_tips: bool


def _run_llm_node(state: ExplainState, prompt: str) -> dict[str, Any]:
    llm = get_llm()
    prompt += MODE_ADDENDA.get(state.get("mode", DEFAULT_MODE), "")
    if state.get("gas_tips"):
        prompt += GAS_TIPS_ADDENDUM
    response = llm.invoke([SystemMessage(content=prompt), *state["messages"]])
    return {"messages": [response]}


def _route(state: ExplainState) -> str:
    return "diagnose" if state.get("reverted") else "explain"


def build_graph(checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """Given messages (tx context) plus a `reverted` flag, explain or diagnose.

    Branches on `reverted` because a failed transaction needs a different
    prompt (root cause + next steps) than a successful one (what happened) —
    this is the branch ADR 0002 anticipated when it justified LangGraph over
    a single LLM call. `mode` (developer/support/auditor) and `gas_tips`
    (opt-in gas efficiency section) don't need their own branches: both only
    add instructions to whichever base prompt `reverted` already picked (see
    `MODE_ADDENDA`/`GAS_TIPS_ADDENDUM`), independently of each other.
    """
    graph = StateGraph(ExplainState)
    graph.add_node("explain", partial(_run_llm_node, prompt=EXPLAIN_SYSTEM_PROMPT))
    graph.add_node("diagnose", partial(_run_llm_node, prompt=DIAGNOSE_SYSTEM_PROMPT))
    graph.add_conditional_edges(START, _route, {"explain": "explain", "diagnose": "diagnose"})
    graph.add_edge("explain", END)
    graph.add_edge("diagnose", END)
    return graph.compile(checkpointer=checkpointer)
