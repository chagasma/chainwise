import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# Default attrs every LogRecord has, so we can compute `extra` fields as the diff.
_RESERVED = logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()


class JSONFormatter(logging.Formatter):
    """Renders log records as single-line JSON for log-aggregator ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = {k: v for k, v in record.__dict__.items() if k not in _RESERVED}
        payload.update(extra)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # Access logs stay on uvicorn's own logger; route them through the same formatter.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
