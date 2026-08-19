from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from chainwise.api import router
from chainwise.config import get_settings
from chainwise.observability import configure_logging, get_logger
from chainwise.observability.middleware import request_context_middleware

settings = get_settings()
logger = get_logger("chainwise")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    configure_logging(settings.log_level)
    logger.info(
        "chainwise_startup",
        extra={"environment": settings.environment, "port": settings.port},
    )
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.middleware("http")(request_context_middleware)
app.include_router(router)
