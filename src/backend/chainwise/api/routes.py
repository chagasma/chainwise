from fastapi import APIRouter, Depends, HTTPException, Query, Request
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from chainwise.adapters import AdapterError, AdapterNotFoundError, BlockscoutClient
from chainwise.api.schemas import (
    ExplanationMode,
    ExplanationResponse,
    GreetingResponse,
    LLMPromptPayload,
    TransactionSummary,
)
from chainwise.cache import ttl_cache
from chainwise.config import NetworkConfig, Settings, get_settings, load_network
from chainwise.models import DEFAULT_MODE, RepoGroundingResult
from chainwise.observability import get_logger
from chainwise.services import detect_risk_patterns, enrich_tokens, ground_transaction

logger = get_logger("chainwise.api")

router = APIRouter()


def get_network(settings: Settings = Depends(get_settings)) -> NetworkConfig:
    return load_network(settings.network)


def get_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.graph


def _translate_adapter_error(exc: Exception, source_name: str) -> HTTPException:
    """Maps an adapter failure to the HTTP response it should become.

    Shared by every route that talks to an external adapter, so a new
    adapter (RPC, GitHub, ...) gets consistent error handling for free
    instead of each route re-deriving its own status-code mapping.
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
    """The decoded function name + parameters, whichever source has them.

    Prefers the explorer's own decode (`summary.decoded_input`); falls back
    to repo grounding, same precedence `_build_prompt_payload` already uses
    to decide whether grounding was worth attempting.
    """
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

    # Repo grounding only runs when the network's abi_strategy allows it and
    # the explorer itself had no ABI to decode the call with.
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
    repo grounding managed to decode it.

    Excludes a plain ETH transfer (`raw_input in (None, "0x")`): a bare
    transfer has nothing to decode because there's no calldata, not because
    data is missing, so it shouldn't trigger a clarifying question. Single
    source of truth for the condition, used both to pick the graph's
    "clarify" branch and to set the response's `needs_clarification` flag —
    they must always agree.
    """
    has_calldata = payload.summary.raw_input not in (None, "0x")
    return has_calldata and payload.summary.decoded_input is None and payload.grounding is None


def _thread_id(tx_hash: str, mode: ExplanationMode, gas_tips: bool) -> str:
    """Isolates the checkpointed conversation per (mode, gas_tips) combination.

    The all-default case (DEFAULT_MODE, no gas tips) keeps thread_id ==
    tx_hash, so existing checkpoints/tests are unaffected; any other
    combination gets its own thread so, e.g., a support-toned answer never
    lands in an auditor's message history for the same tx.
    """
    suffix = "" if mode == DEFAULT_MODE else f":{mode}"
    if gas_tips:
        suffix += ":gas"
    return tx_hash + suffix


def _run_agent(
    graph: CompiledStateGraph,
    payload: LLMPromptPayload,
    tx_hash: str,
    mode: ExplanationMode,
    gas_tips: bool,
) -> tuple[str, str]:
    thread_id = _thread_id(tx_hash, mode, gas_tips)
    initial_state = {
        "messages": [HumanMessage(content=payload.model_dump_json(indent=2))],
        "reverted": payload.summary.status == "reverted",
        "undecoded": _is_undecoded(payload),
        "mode": mode,
        "gas_tips": gas_tips,
    }
    try:
        result = graph.invoke(initial_state, config={"configurable": {"thread_id": thread_id}})
    except Exception as exc:
        # Provider SDKs raise a wide variety of exception types (connection,
        # rate limit, auth, malformed response, ...) — any of them must
        # degrade to a clear 502 rather than an unhandled 500. Logged with
        # its real type/traceback here so a genuine bug in our own node code
        # isn't mistaken for a provider outage when reading logs later.
        logger.error("llm_explanation_failed", exc_info=exc, extra={"tx_hash": tx_hash})
        raise HTTPException(status_code=502, detail=f"LLM explanation unavailable: {exc}") from exc
    return result["messages"][-1].content, thread_id


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
