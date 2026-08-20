import base64
from typing import Any

import httpx

from chainwise.adapters.base import HttpAdapter
from chainwise.adapters.errors import AdapterError, AdapterNotFoundError


class GitHubError(AdapterError):
    """Raised when the GitHub API can't be reached or returns an unexpected response."""


class GitHubNotFoundError(AdapterNotFoundError, GitHubError):
    """Raised when a requested repo path doesn't exist."""

    def __init__(self, path: str) -> None:
        super().__init__(f"{path} not found on GitHub")


class GitHubRateLimitedError(GitHubError):
    """Raised when GitHub's API rate limit is exhausted.

    Common when `github_token` isn't configured: unauthenticated requests to
    the Code Search API get a few requests per minute. Distinguished from a
    generic `GitHubError` so callers can log/skip without treating it as a
    real outage.
    """


class GitHubClient(HttpAdapter):
    """Thin client over the GitHub REST API (code search, file contents).

    Methods return the API's parsed JSON (or decoded file text) as-is —
    interpreting it (is this an ABI artifact? which function matches?) is
    the caller's job, same split as BlockscoutClient/RPCClient.
    """

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: str | None = None,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.Client(
            base_url=self.BASE_URL,
            timeout=timeout,
            transport=transport or self._default_transport(),
            headers=headers,
        )

    def search_code(self, repo: str, query: str) -> list[dict[str, Any]]:
        """Searches for files matching `query` within `repo` ("owner/name")."""
        data = self._get("/search/code", params={"q": f"{query} repo:{repo}"})
        return data.get("items", [])

    def get_file_content(self, repo: str, path: str) -> str:
        """Fetches and decodes the text content of a single file at `path` in `repo`."""
        data = self._get(f"/repos/{repo}/contents/{path}")
        if isinstance(data, list):
            raise GitHubError(f"{path} is a directory, not a file")
        content = data.get("content", "")
        if data.get("encoding") == "base64":
            return base64.b64decode(content).decode("utf-8")
        return content

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        try:
            response = self._client.get(path, params=params)
        except httpx.HTTPError as exc:
            raise GitHubError(f"Could not reach GitHub: {exc}") from exc
        if response.status_code == 404:
            raise GitHubNotFoundError(path)
        if response.status_code in (403, 429) and response.headers.get(
            "x-ratelimit-remaining"
        ) == "0":
            raise GitHubRateLimitedError("GitHub API rate limit exceeded")
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubError(f"GitHub returned {response.status_code} for {path}") from exc
        return response.json()
