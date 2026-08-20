from chainwise.api.routes import _reset_thread
from chainwise.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_greet_returns_hello_message() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello, ChainWise!"}


def test_greet_response_carries_request_id_header() -> None:
    response = client.get("/")

    assert "X-Request-ID" in response.headers


class _FakeCheckpointer:
    def __init__(self) -> None:
        self.deleted_thread_ids: list[str] = []

    def delete_thread(self, thread_id: str) -> None:
        self.deleted_thread_ids.append(thread_id)


class _GraphWithCheckpointer:
    def __init__(self, checkpointer: _FakeCheckpointer) -> None:
        self.checkpointer = checkpointer


class _GraphWithoutCheckpointer:
    """Mimics the plain stub graphs used in other route tests: no `.checkpointer`."""


def test_reset_thread_wipes_prior_checkpoint_when_checkpointer_present() -> None:
    checkpointer = _FakeCheckpointer()

    _reset_thread(_GraphWithCheckpointer(checkpointer), "0xabc")  # type: ignore[arg-type]

    assert checkpointer.deleted_thread_ids == ["0xabc"]


def test_reset_thread_is_a_noop_without_a_real_checkpointer() -> None:
    # Must not raise on the plain fakes other route tests pass as `graph`.
    _reset_thread(_GraphWithoutCheckpointer(), "0xabc")  # type: ignore[arg-type]
