from fastapi import APIRouter, Depends, HTTPException, Query, Request
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from chainwise.adapters import AdapterError, AdapterNotFoundError, BlockscoutClient
from chainwise.agent.graph import ExplainState, ExplainStateExtra
from chainwise.api.schemas import (
    ExplanationMode,
    ExplanationResponse,
    GreetingResponse,
    LLMPromptPayload,
    MultiTransactionAnalysisResponse,
    MultiTransactionPayload,
    TransactionSummary,
)
from chainwise.cache import ttl_cache
from chainwise.config import NetworkConfig, Settings, get_settings, load_network
from chainwise.models import DEFAULT_MODE, RepoGroundingResult
from chainwise.observability import get_logger
from chainwise.services import (
    detect_relations,
    detect_risk_patterns,
    enrich_tokens,
    ground_transaction,
)

logger = get_logger("chainwise.api")

router = APIRouter()


def get_network(settings: Settings = Depends(get_settings)) -> NetworkConfig:
    return load_network(settings.network)


def get_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.graph


def _translate_adapter_error(exc: Exception, source_name: str) -> HTTPException:
    """Maps an adapter failure to the HTTP response it should become.

    Shared by every route that talks to an external adapter.
    """
    if isinstance(exc, AdapterNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, AdapterError):
        return HTTPException(status_code=502, detail=f"{source_name} is unavailable: {exc}")
    return HTTPException(
        status_code=502, detail=f"{source_name} returned an unexpected response: {exc}"
    )


@router.get("/", response_model=GreetingResponse)
def greet() -> GreetingResponse:
    return GreetingResponse(message="Hello, ChainWise!")


@router.get("/network", response_model=NetworkConfig)
def active_network(network: NetworkConfig = Depends(get_network)) -> NetworkConfig:
    return network


@ttl_cache(seconds=30)
def _get_transaction_summary(tx_hash: str, network: NetworkConfig) -> TransactionSummary:
    with BlockscoutClient(network.explorer_url) as client:
        try:
            tx = client.get_transaction(tx_hash)
            logs = client.get_transaction_logs(tx_hash)
            return TransactionSummary.from_blockscout(tx, logs, network.explorer_url)
        except (AdapterError, KeyError, TypeError, ValidationError) as exc:
            raise _translate_adapter_error(exc, f"Explorer for '{network.name}'") from exc


@router.get("/tx/{tx_hash}", response_model=TransactionSummary)
def get_transaction(
    tx_hash: str, network: NetworkConfig = Depends(get_network)
) -> TransactionSummary:
    return _get_transaction_summary(tx_hash, network)


def _decoded_call(
    summary: TransactionSummary, grounding: RepoGroundingResult | None
) -> tuple[str | None, dict[str, str]]:
    """The decoded function name + parameters: prefers the explorer's own
    decode, falls back to repo grounding."""
    if summary.decoded_input:
        method_call = summary.decoded_input.get("method_call") or ""
        function_name = method_call.split("(", 1)[0] or None
        params = {
            p["name"]: str(p.get("value"))
            for p in summary.decoded_input.get("parameters") or []
            if p.get("name")
        }
        return function_name, params
    if grounding:
        return grounding.decoded_call.function, {
            k: str(v) for k, v in grounding.decoded_call.parameters.items()
        }
    return None, {}


def _build_prompt_payload(
    summary: TransactionSummary, network: NetworkConfig, settings: Settings
) -> LLMPromptPayload:
    transfer_addresses = {
        log.address
        for log in summary.logs
        if log.event and log.event.split("(", 1)[0] == "Transfer"
    }
    tokens = enrich_tokens(transfer_addresses, network)

    # Only when the explorer had no ABI and the network allows repo grounding.
    grounding = None
    if summary.decoded_input is None and "repo" in network.abi_strategy:
        grounding = ground_transaction(summary.raw_input, network, settings.github_token)

    function_name, params = _decoded_call(summary, grounding)
    security_findings = detect_risk_patterns(function_name, params)

    return LLMPromptPayload(
        summary=summary, tokens=tokens, grounding=grounding, security_findings=security_findings
    )


def _is_undecoded(payload: LLMPromptPayload) -> bool:
    """True when there was a real call to decode and neither the explorer nor
    repo grounding managed to decode it. Excludes a plain ETH transfer
    (no calldata to decode in the first place). Single source of truth,
    used both for the graph's "clarify" branch and `needs_clarification`.
    """
    has_calldata = payload.summary.raw_input not in (None, "0x")
    return has_calldata and payload.summary.decoded_input is None and payload.grounding is None


def _mode_suffix(mode: ExplanationMode) -> str:
    """`""` for DEFAULT_MODE (keeps existing thread ids unaffected), else `:{mode}`."""
    return "" if mode == DEFAULT_MODE else f":{mode}"


def _thread_id(tx_hash: str, mode: ExplanationMode, gas_tips: bool) -> str:
    """Isolates the checkpointed conversation per (mode, gas_tips) combination,
    so e.g. a support-toned answer never lands in an auditor's history."""
    suffix = _mode_suffix(mode)
    if gas_tips:
        suffix += ":gas"
    return tx_hash + suffix


def _invoke_agent(
    graph: CompiledStateGraph, content: str, thread_id: str, state_extra: ExplainStateExtra
) -> str:
    """Runs the agent graph and unwraps its final message, or degrades to a 502.
    Shared by every route that talks to the LLM."""
    initial_state: ExplainState = {"messages": [HumanMessage(content=content)], **state_extra}
    try:
        result = graph.invoke(initial_state, config={"configurable": {"thread_id": thread_id}})
    except Exception as exc:
        # Provider SDKs raise many exception types; degrade all of them to a
        # clear 502 with the real traceback logged, instead of an unhandled 500.
        logger.error("llm_explanation_failed", exc_info=exc, extra={"thread_id": thread_id})
        raise HTTPException(status_code=502, detail=f"LLM explanation unavailable: {exc}") from exc
    return result["messages"][-1].content


def _run_agent(
    graph: CompiledStateGraph,
    payload: LLMPromptPayload,
    tx_hash: str,
    mode: ExplanationMode,
    gas_tips: bool,
) -> tuple[str, str]:
    thread_id = _thread_id(tx_hash, mode, gas_tips)
    state_extra: ExplainStateExtra = {
        "reverted": payload.summary.status == "reverted",
        "undecoded": _is_undecoded(payload),
        "mode": mode,
        "gas_tips": gas_tips,
    }
    explanation = _invoke_agent(graph, payload.model_dump_json(indent=2), thread_id, state_extra)
    return explanation, thread_id


@router.get("/tx/{tx_hash}/explain", response_model=ExplanationResponse)
def explain_transaction(
    tx_hash: str,
    mode: ExplanationMode = Query(DEFAULT_MODE, description="Audience for the explanation."),
    gas_tips: bool = Query(False, description="Add a gas-efficiency section."),
    network: NetworkConfig = Depends(get_network),
    settings: Settings = Depends(get_settings),
    graph: CompiledStateGraph = Depends(get_graph),
) -> ExplanationResponse:
    summary = _get_transaction_summary(tx_hash, network)
    payload = _build_prompt_payload(summary, network, settings)
    explanation, thread_id = _run_agent(graph, payload, tx_hash, mode, gas_tips)
    return ExplanationResponse(
        summary=payload.summary,
        tokens=payload.tokens,
        grounding=payload.grounding,
        security_findings=payload.security_findings,
        explanation=explanation,
        needs_clarification=_is_undecoded(payload),
        thread_id=thread_id,
        mode=mode,
        gas_tips=gas_tips,
    )


def _multi_thread_id(hashes: list[str], mode: ExplanationMode) -> str:
    """Same isolation idea as `_thread_id`, keyed on the whole (sorted, deduped) hash set."""
    return "multi:" + "+".join(hashes) + _mode_suffix(mode)


@router.get("/analyze", response_model=MultiTransactionAnalysisResponse)
def analyze_transactions(
    hash: list[str] = Query(
        ..., description="2+ transaction hashes to analyze together, e.g. ?hash=0x..&hash=0x.."
    ),
    mode: ExplanationMode = Query(DEFAULT_MODE, description="Audience for the explanation."),
    network: NetworkConfig = Depends(get_network),
    settings: Settings = Depends(get_settings),
    graph: CompiledStateGraph = Depends(get_graph),
) -> MultiTransactionAnalysisResponse:
    """Explains a set of related transactions together, citing detected relations between them."""
    hashes = list(dict.fromkeys(hash))  # dedupe, preserve caller's order
    if len(hashes) < 2:
        raise HTTPException(
            status_code=400, detail="Provide at least 2 distinct transaction hashes."
        )

    summaries = [_get_transaction_summary(h, network) for h in hashes]
    summaries.sort(key=lambda s: (s.block_number is None, s.block_number or 0))

    payloads = [_build_prompt_payload(s, network, settings) for s in summaries]
    relations = detect_relations([(s.hash, s.from_address, s.to_address) for s in summaries])
    multi_payload = MultiTransactionPayload(transactions=payloads, relations=relations)

    thread_id = _multi_thread_id([s.hash for s in summaries], mode)
    state_extra: ExplainStateExtra = {"multi": True, "mode": mode}
    explanation = _invoke_agent(
        graph, multi_payload.model_dump_json(indent=2), thread_id, state_extra
    )

    return MultiTransactionAnalysisResponse(
        transactions=payloads,
        relations=relations,
        explanation=explanation,
        thread_id=thread_id,
        mode=mode,
    )
