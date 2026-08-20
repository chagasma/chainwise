from typing import Any

import httpx

from chainwise.adapters.base import HttpAdapter
from chainwise.adapters.errors import AdapterError


class RPCError(AdapterError):
    """Raised when the RPC endpoint can't be reached or returns a JSON-RPC error."""


class RPCClient(HttpAdapter):
    """Thin client over a network's JSON-RPC endpoint (eth_call).

    Methods return raw hex strings — ABI encoding of call data and decoding
    of results is the caller's job (mirrors BlockscoutClient: adapters stay
    dumb HTTP clients, services own interpreting the data).
    """

    def __init__(
        self,
        rpc_url: str,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._rpc_url = rpc_url
        self._client = httpx.Client(
            timeout=timeout, transport=transport or self._default_transport()
        )
        self._next_id = 1

    def eth_call(self, to: str, data: str, block: str = "latest") -> str:
        """Read-only contract call. `data` is the ABI-encoded selector+args hex string."""
        return self._request("eth_call", [{"to": to, "data": data}, block])

    def _request(self, method: str, params: list[Any]) -> str:
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": self._next_id}
        self._next_id += 1
        try:
            response = self._client.post(self._rpc_url, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RPCError(f"Could not reach RPC endpoint: {exc}") from exc
        body = response.json()
        if "error" in body:
            raise RPCError(f"RPC {method} failed: {body['error'].get('message', body['error'])}")
        return body["result"]
