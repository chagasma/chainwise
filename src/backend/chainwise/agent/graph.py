from functools import partial
from typing import Any

from langchain_core.messages import SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from chainwise.agent.llm import get_llm
from chainwise.agent.prompts import (
    CLARIFY_SYSTEM_PROMPT,
    DIAGNOSE_SYSTEM_PROMPT,
    EXPLAIN_SYSTEM_PROMPT,
    GAS_TIPS_ADDENDUM,
    MODE_ADDENDA,
    MULTI_TX_SYSTEM_PROMPT,
)
from chainwise.models import DEFAULT_MODE, ExplanationMode


class ExplainStateExtra(TypedDict, total=False):
    """The routing flags on top of `messages`, split out so `state_extra` in
    api/routes.py (which has the flags but not `messages` yet) can be typed."""

    reverted: bool
    undecoded: bool
    multi: bool
    mode: ExplanationMode
    gas_tips: bool


class ExplainState(MessagesState, ExplainStateExtra):
    """Shared state for every /tx/... endpoint the agent serves, not just the
    single-transaction explain/diagnose/clarify flow the name comes from —
    `multi` (see `_route`) is the multi-transaction analysis flow."""


def _run_llm_node(state: ExplainState, prompt: str) -> dict[str, Any]:
    llm = get_llm()
    prompt += MODE_ADDENDA.get(state.get("mode", DEFAULT_MODE), "")
    if state.get("gas_tips"):
        prompt += GAS_TIPS_ADDENDUM
    response = llm.invoke([SystemMessage(content=prompt), *state["messages"]])
    return {"messages": [response]}


def _route(state: ExplainState) -> str:
    # `multi` is a different request shape (set only by /analyze) so it wins
    # outright; `reverted` wins over `undecoded` — knowing a tx failed is
    # more useful than blocking on a clarifying question for a done deal.
    if state.get("multi"):
        return "analyze_multi"
    if state.get("reverted"):
        return "diagnose"
    if state.get("undecoded"):
        return "clarify"
    return "explain"


def build_graph(checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """Routes on `multi`/`reverted`/`undecoded` to one of 4 single-LLM-call
    nodes, each with its own system prompt (see `_route`, ADR 0002). `mode`
    and `gas_tips` don't need their own branches: they just add instructions
    to whichever base prompt was picked (`MODE_ADDENDA`/`GAS_TIPS_ADDENDUM`).
    """
    graph = StateGraph(ExplainState)
    graph.add_node("explain", partial(_run_llm_node, prompt=EXPLAIN_SYSTEM_PROMPT))
    graph.add_node("diagnose", partial(_run_llm_node, prompt=DIAGNOSE_SYSTEM_PROMPT))
    graph.add_node("clarify", partial(_run_llm_node, prompt=CLARIFY_SYSTEM_PROMPT))
    graph.add_node("analyze_multi", partial(_run_llm_node, prompt=MULTI_TX_SYSTEM_PROMPT))
    graph.add_conditional_edges(
        START,
        _route,
        {
            "explain": "explain",
            "diagnose": "diagnose",
            "clarify": "clarify",
            "analyze_multi": "analyze_multi",
        },
    )
    graph.add_edge("explain", END)
    graph.add_edge("diagnose", END)
    graph.add_edge("clarify", END)
    graph.add_edge("analyze_multi", END)
    return graph.compile(checkpointer=checkpointer)
