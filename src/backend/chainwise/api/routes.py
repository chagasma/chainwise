from fastapi import APIRouter

from chainwise.api.schemas import GreetingResponse

router = APIRouter()


@router.get("/", response_model=GreetingResponse)
def greet() -> GreetingResponse:
    return GreetingResponse(message="Hello, ChainWise!")
