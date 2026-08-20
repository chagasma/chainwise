import base64

import httpx
import pytest
from chainwise.adapters import (
    GitHubClient,
    GitHubError,
    GitHubNotFoundError,
    GitHubRateLimitedError,
)

REPO = "ethereum/go-ethereum"


def _client(handler: httpx.MockTransport, token: str | None = None) -> GitHubClient:
    return GitHubClient(token=token, transport=handler)


def test_search_code_returns_items() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"items": [{"path": "abi/Token.json"}]})
    )

    with _client(transport) as client:
        assert client.search_code(REPO, '"stateMutability"') == [{"path": "abi/Token.json"}]


def test_search_code_sends_repo_scoped_query() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["q"] = request.url.params["q"]
        return httpx.Response(200, json={"items": []})

    with _client(httpx.MockTransport(handler)) as client:
        client.search_code(REPO, '"stateMutability" extension:json')

    assert captured["q"] == f'"stateMutability" extension:json repo:{REPO}'


def test_search_code_sends_auth_header_when_token_given() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"items": []})

    with _client(httpx.MockTransport(handler), token="ghp_secret") as client:
        client.search_code(REPO, "query")

    assert captured["auth"] == "Bearer ghp_secret"


def test_search_code_omits_auth_header_without_token() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"items": []})

    with _client(httpx.MockTransport(handler)) as client:
        client.search_code(REPO, "query")

    assert captured["auth"] is None


def test_get_file_content_decodes_base64() -> None:
    raw = '{"abi": []}'
    encoded = base64.b64encode(raw.encode()).decode()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"content": encoded, "encoding": "base64"})
    )

    with _client(transport) as client:
        assert client.get_file_content(REPO, "abi/Token.json") == raw


def test_get_file_content_raises_when_path_is_a_directory() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=[{"path": "a"}]))

    with _client(transport) as client, pytest.raises(GitHubError, match="directory"):
        client.get_file_content(REPO, "abi")


def test_search_code_raises_not_found_on_404() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(404, json={}))

    with _client(transport) as client, pytest.raises(GitHubNotFoundError):
        client.search_code(REPO, "query")


def test_search_code_raises_rate_limited_on_exhausted_quota() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(403, headers={"x-ratelimit-remaining": "0"}, json={})
    )

    with _client(transport) as client, pytest.raises(GitHubRateLimitedError):
        client.search_code(REPO, "query")


def test_search_code_raises_generic_error_on_other_403() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(403, headers={"x-ratelimit-remaining": "12"}, json={})
    )

    with _client(transport) as client, pytest.raises(GitHubError):
        client.search_code(REPO, "query")


def test_search_code_raises_on_connection_failure() -> None:
    def raise_connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with _client(httpx.MockTransport(raise_connect_error)) as client, pytest.raises(GitHubError):
        client.search_code(REPO, "query")
