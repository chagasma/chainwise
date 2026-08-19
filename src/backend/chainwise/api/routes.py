from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from chainwise.adapters import BlockscoutClient, BlockscoutError, TransactionNotFoundError
from chainwise.api.schemas import GreetingResponse, TransactionSummary
from chainwise.config import NetworkConfig, get_settings, load_network

router = APIRouter()


@router.get("/", response_model=GreetingResponse)
def greet() -> GreetingResponse:
    return GreetingResponse(message="Hello, ChainWise!")


@router.get("/network", response_model=NetworkConfig)
def active_network() -> NetworkConfig:
    settings = get_settings()
    return load_network(settings.network)


@router.get("/tx/{tx_hash}", response_model=TransactionSummary)
def get_transaction(tx_hash: str) -> TransactionSummary:
    settings = get_settings()
    network = load_network(settings.network)

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
