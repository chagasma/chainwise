from fastapi import APIRouter

from chainwise.api.schemas import GreetingResponse
from chainwise.config import NetworkConfig, get_settings, load_network

router = APIRouter()


@router.get("/", response_model=GreetingResponse)
def greet() -> GreetingResponse:
    return GreetingResponse(message="Hello, ChainWise!")


@router.get("/network", response_model=NetworkConfig)
def active_network() -> NetworkConfig:
    settings = get_settings()
    return load_network(settings.network)
