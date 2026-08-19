from collections.abc import Callable, Iterator
from typing import Any

import chainwise.api.routes as routes_module
import pytest
from chainwise.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


class _FakeBlockscoutClient:
    """Stands in for BlockscoutClient so tests never hit the network."""

    def __init__(self, tx: dict[str, Any], logs: list[dict[str, Any]] | None = None) -> None:
        self._tx = tx
        self._logs = logs or []

    def __call__(self, *_args: Any, **_kwargs: Any) -> "_FakeBlockscoutClient":
        return self

    def __enter__(self) -> "_FakeBlockscoutClient":
        return self

    def __exit__(self, *_exc: Any) -> None:
        return None

    def get_transaction(self, _tx_hash: str) -> dict[str, Any]:
        return self._tx

    def get_transaction_logs(self, _tx_hash: str) -> list[dict[str, Any]]:
        return self._logs


@pytest.fixture
def patch_blockscout_client() -> Iterator[Callable[[dict[str, Any]], None]]:
    original = routes_module.BlockscoutClient

    def _patch(tx: dict[str, Any]) -> None:
        routes_module.BlockscoutClient = _FakeBlockscoutClient(tx)  # type: ignore[assignment]

    yield _patch
    routes_module.BlockscoutClient = original


def test_get_transaction_returns_502_when_explorer_payload_is_malformed(
    patch_blockscout_client: Callable[[dict[str, Any]], None],
) -> None:
    patch_blockscout_client({"status": "ok"})  # missing required "hash"/"from"

    response = client.get("/tx/0xdeadbeef")

    assert response.status_code == 502
    assert "unexpected response" in response.json()["detail"]
