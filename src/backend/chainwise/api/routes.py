from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from chainwise.adapters import AdapterError, AdapterNotFoundError, BlockscoutClient
from chainwise.agent import EXPLAIN_SYSTEM_PROMPT
from chainwise.api.schemas import ExplanationResponse, GreetingResponse, TransactionSummary
from chainwise.config import NetworkConfig, Settings, get_settings, load_network
from chainwise.observability import get_logger

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


@router.get("/tx/{tx_hash}/explain", response_model=ExplanationResponse)
def explain_transaction(
    tx_hash: str,
    network: NetworkConfig = Depends(get_network),
    graph: CompiledStateGraph = Depends(get_graph),
) -> ExplanationResponse:
    summary = _get_transaction_summary(tx_hash, network)

    initial_state = {
        "messages": [
            SystemMessage(content=EXPLAIN_SYSTEM_PROMPT),
            HumanMessage(content=summary.model_dump_json(indent=2)),
        ]
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

    explanation = result["messages"][-1].content
    return ExplanationResponse(summary=summary, explanation=explanation, thread_id=tx_hash)
