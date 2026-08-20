from fastapi import APIRouter, Depends, HTTPException, Request
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from chainwise.adapters import BlockscoutClient, BlockscoutError, TransactionNotFoundError
from chainwise.agent import EXPLAIN_SYSTEM_PROMPT
from chainwise.api.schemas import ExplanationResponse, GreetingResponse, TransactionSummary
from chainwise.config import NetworkConfig, get_settings, load_network
from chainwise.observability import get_logger

logger = get_logger("chainwise.api")

router = APIRouter()


@router.get("/", response_model=GreetingResponse)
def greet() -> GreetingResponse:
    return GreetingResponse(message="Hello, ChainWise!")


@router.get("/network", response_model=NetworkConfig)
def active_network() -> NetworkConfig:
    settings = get_settings()
    return load_network(settings.network)


def get_graph(request: Request) -> CompiledStateGraph:
    return request.app.state.graph


def _get_transaction_summary(tx_hash: str, network: NetworkConfig) -> TransactionSummary:
    with BlockscoutClient(network.explorer_url) as client:
        try:
            tx = client.get_transaction(tx_hash)
            logs = client.get_transaction_logs(tx_hash)
            return TransactionSummary.from_blockscout(tx, logs, network.explorer_url)
        except TransactionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except BlockscoutError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Explorer for '{network.name}' is unavailable: {exc}",
            ) from exc
        except (KeyError, TypeError, ValidationError) as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Explorer for '{network.name}' returned an unexpected response: {exc}",
            ) from exc


@router.get("/tx/{tx_hash}", response_model=TransactionSummary)
def get_transaction(tx_hash: str) -> TransactionSummary:
    settings = get_settings()
    network = load_network(settings.network)
    return _get_transaction_summary(tx_hash, network)


@router.get("/tx/{tx_hash}/explain", response_model=ExplanationResponse)
def explain_transaction(
    tx_hash: str, graph: CompiledStateGraph = Depends(get_graph)
) -> ExplanationResponse:
    settings = get_settings()
    network = load_network(settings.network)
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
