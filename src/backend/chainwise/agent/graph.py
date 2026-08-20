from functools import partial
from typing import Any

from langchain_core.messages import SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph

from chainwise.agent.llm import get_llm
from chainwise.agent.prompts import (
    CLARIFY_SYSTEM_PROMPT,
    DIAGNOSE_SYSTEM_PROMPT,
    EXPLAIN_SYSTEM_PROMPT,
    GAS_TIPS_ADDENDUM,
    MODE_ADDENDA,
)
from chainwise.models import DEFAULT_MODE, ExplanationMode


class ExplainState(MessagesState):
    reverted: bool
    undecoded: bool
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
    # `reverted` wins over `undecoded`: DIAGNOSE_SYSTEM_PROMPT already
    # handles "nothing decoded" gracefully (flags root cause as necessarily
    # speculative), and knowing *that it failed* is more useful than
    # blocking on a clarifying question for a transaction that's done.
    if state.get("reverted"):
        return "diagnose"
    if state.get("undecoded"):
        return "clarify"
    return "explain"


def build_graph(checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    """Given messages (tx context) plus `reverted`/`undecoded` flags, explain/diagnose/clarify.

    Branches on `reverted` because a failed transaction needs a different
    prompt (root cause + next steps) than a successful one (what happened) —
    this is the branch ADR 0002 anticipated when it justified LangGraph over
    a single LLM call. Branches on `undecoded` (decoded_input AND grounding
    both null — nothing to go on) for the same reason: the structured triage
    flow bonus is "ask before concluding", which needs its own prompt
    (CLARIFY_SYSTEM_PROMPT) instructing the LLM to ask one targeted question
    instead of guessing, not just a rule tacked onto EXPLAIN_SYSTEM_PROMPT.
    `mode` (developer/support/auditor) and `gas_tips` (opt-in gas efficiency
    section) don't need their own branches: both only add instructions to
    whichever base prompt was picked (see `MODE_ADDENDA`/`GAS_TIPS_ADDENDUM`),
    independently of each other and of this routing.
    """
    graph = StateGraph(ExplainState)
    graph.add_node("explain", partial(_run_llm_node, prompt=EXPLAIN_SYSTEM_PROMPT))
    graph.add_node("diagnose", partial(_run_llm_node, prompt=DIAGNOSE_SYSTEM_PROMPT))
    graph.add_node("clarify", partial(_run_llm_node, prompt=CLARIFY_SYSTEM_PROMPT))
    graph.add_conditional_edges(
        START, _route, {"explain": "explain", "diagnose": "diagnose", "clarify": "clarify"}
    )
    graph.add_edge("explain", END)
    graph.add_edge("diagnose", END)
    graph.add_edge("clarify", END)
    return graph.compile(checkpointer=checkpointer)
