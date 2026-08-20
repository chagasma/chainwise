from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chainwise.agent import build_graph, create_checkpointer
from chainwise.api import router
from chainwise.config import get_settings
from chainwise.observability import configure_logging, get_logger
from chainwise.observability.middleware import request_context_middleware

settings = get_settings()
logger = get_logger("chainwise")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_logging(settings.log_level)
    logger.info(
        "chainwise_startup",
        extra={"environment": settings.environment, "port": settings.port},
    )
    with create_checkpointer(settings.database_url) as checkpointer:
        app.state.graph = build_graph(checkpointer)
        yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.middleware("http")(request_context_middleware)
# Local dev tool with no auth/session state — the frontend (a different port)
# needs to call this from the browser, and there's nothing here worth
# restricting by origin.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"]
)
app.include_router(router)
