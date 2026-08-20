from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from chainwise.adapters import AdapterError, AdapterNotFoundError, BlockscoutClient
from chainwise.api.schemas import (
    ExplanationResponse,
    GreetingResponse,
    LLMPromptPayload,
    TransactionSummary,
)
from chainwise.config import NetworkConfig, Settings, get_settings, load_network
from chainwise.observability import get_logger
from chainwise.services import enrich_tokens, ground_transaction

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

    return LLMPromptPayload(summary=summary, tokens=tokens, grounding=grounding)


def _run_agent(graph: CompiledStateGraph, payload: LLMPromptPayload, tx_hash: str) -> str:
    initial_state = {
        "messages": [HumanMessage(content=payload.model_dump_json(indent=2))],
        "reverted": payload.summary.status == "reverted",
    }
    try:
        result = graph.invoke(initial_state, config={"configurable": {"thread_id": tx_hash}})
    except Exception as exc:
        # Provider SDKs raise a wide variety of exception types (connection,
        # rate limit, auth, malformed response, ...) — any of them must
        # degrade to a clear 502 rather than an unhandled 500. Logged with
        # its real type/traceback here so a genuine bug in our own node code
        # isn't mistaken for a provider outage when reading logs later.
        logger.error("llm_explanation_failed", exc_info=exc, extra={"tx_hash": tx_hash})
        raise HTTPException(status_code=502, detail=f"LLM explanation unavailable: {exc}") from exc
    return result["messages"][-1].content


@router.get("/tx/{tx_hash}/explain", response_model=ExplanationResponse)
def explain_transaction(
    tx_hash: str,
    network: NetworkConfig = Depends(get_network),
    settings: Settings = Depends(get_settings),
    graph: CompiledStateGraph = Depends(get_graph),
) -> ExplanationResponse:
    summary = _get_transaction_summary(tx_hash, network)
    payload = _build_prompt_payload(summary, network, settings)
    explanation = _run_agent(graph, payload, tx_hash)
    return ExplanationResponse(
        summary=payload.summary,
        tokens=payload.tokens,
        grounding=payload.grounding,
        explanation=explanation,
        thread_id=tx_hash,
    )
