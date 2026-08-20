from typing import Any

import httpx

from chainwise.adapters.base import HttpAdapter
from chainwise.adapters.errors import AdapterError, AdapterNotFoundError


class BlockscoutError(AdapterError):
    """Raised when the explorer can't be reached or returns an unexpected response."""


class TransactionNotFoundError(AdapterNotFoundError, BlockscoutError):
    """Raised when the explorer has no record of the given transaction hash."""

    def __init__(self, tx_hash: str) -> None:
        super().__init__(f"Transaction {tx_hash} not found on this network's explorer")


class BlockscoutClient(HttpAdapter):
    """Thin client over the Blockscout v2 API (transaction, receipt, logs).

    Methods return the explorer's raw JSON as `dict[str, Any]` — shape
    validation and translation into domain schemas is the caller's job
    (see `TransactionSummary.from_blockscout`). Adapters stay dumb HTTP
    clients; schemas own interpreting the wire format.
    """

    def __init__(
        self,
        explorer_url: str,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=explorer_url.rstrip("/"), timeout=timeout, transport=transport
        )

    def get_transaction(self, tx_hash: str) -> dict[str, Any]:
        return self._get(f"/api/v2/transactions/{tx_hash}", tx_hash)

    def get_transaction_logs(self, tx_hash: str) -> list[dict[str, Any]]:
        data = self._get(f"/api/v2/transactions/{tx_hash}/logs", tx_hash)
        return data.get("items", [])

    def _get(self, path: str, tx_hash: str) -> dict[str, Any]:
        try:
            response = self._client.get(path)
        except httpx.HTTPError as exc:
            raise BlockscoutError(f"Could not reach explorer: {exc}") from exc
        if response.status_code == 404:
            raise TransactionNotFoundError(tx_hash)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise BlockscoutError(
                f"Explorer returned {response.status_code} for {tx_hash}"
            ) from exc
        return response.json()
