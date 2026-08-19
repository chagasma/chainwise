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
