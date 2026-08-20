from types import TracebackType
from typing import Self

import httpx


class HttpAdapter:
    """Owns the httpx.Client lifecycle shared by every adapter (Blockscout, RPC, GitHub).

    Adapters differ only in base URL/headers and endpoint methods; the
    context-manager plumbing is identical across all of them.
    """

    _client: httpx.Client

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
