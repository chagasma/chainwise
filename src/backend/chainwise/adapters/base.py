from types import TracebackType
from typing import Self

import httpx


class HttpAdapter:
    """Owns the httpx.Client lifecycle shared by every adapter (Blockscout, RPC, GitHub).

    Adapters differ only in base URL/headers and endpoint methods; the
    context-manager plumbing is identical across all of them.
    """

    _client: httpx.Client

    @staticmethod
    def _default_transport(retries: int = 2) -> httpx.HTTPTransport:
        """A transport that retries connection failures — httpx's own retry support.

        Only used when the caller didn't pass one (production); tests always
        pass an `httpx.MockTransport`, so this never touches real network I/O
        in the suite. Doesn't retry on HTTP error status codes, only on
        connection-level failures (DNS, refused, timeout on connect).
        """
        return httpx.HTTPTransport(retries=retries)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
