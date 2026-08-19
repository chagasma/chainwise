import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from chainwise.observability.logging import get_logger

logger = get_logger("chainwise.access")

REQUEST_ID_HEADER = "X-Request-ID"


async def request_context_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Assigns a request id, times the request, and emits one structured access log."""
    request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
    started_at = time.perf_counter()

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers[REQUEST_ID_HEADER] = request_id
    logger.info(
        "request_handled",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response
