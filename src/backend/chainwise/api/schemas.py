from typing import Any, Literal, Self

from pydantic import BaseModel


class GreetingResponse(BaseModel):
    message: str


class LogEntry(BaseModel):
    address: str
    event: str | None
    decoded: dict[str, Any] | None


class TransactionSummary(BaseModel):
    """A human-friendly view of a transaction, grounded in explorer data."""

    hash: str
    status: Literal["success", "reverted", "pending"]
    block_number: int | None
    timestamp: str | None
    from_address: str
    to_address: str | None
    value_wei: str
    gas_used: int | None
    fee_wei: str | None
    method: str | None
    decoded_input: dict[str, Any] | None
    revert_reason: str | None
    logs: list[LogEntry]
    source_url: str

    @classmethod
    def from_blockscout(
        cls, tx: dict[str, Any], logs: list[dict[str, Any]], explorer_url: str
    ) -> Self:
        status_map: dict[str, Literal["success", "reverted"]] = {
            "ok": "success",
            "error": "reverted",
        }
        raw_status: str = tx.get("status") or ""
        return cls(
            hash=tx["hash"],
            status=status_map.get(raw_status, "pending"),
            block_number=tx.get("block_number"),
            timestamp=tx.get("timestamp"),
            from_address=tx["from"]["hash"],
            to_address=(tx.get("to") or {}).get("hash"),
            value_wei=tx.get("value", "0"),
            gas_used=tx.get("gas_used"),
            fee_wei=(tx.get("fee") or {}).get("value"),
            method=tx.get("method"),
            decoded_input=tx.get("decoded_input"),
            revert_reason=tx.get("revert_reason"),
            logs=[
                LogEntry(
                    address=log["address"]["hash"],
                    event=(log.get("decoded") or {}).get("method_call"),
                    decoded=log.get("decoded"),
                )
                for log in logs
            ],
            source_url=f"{explorer_url.rstrip('/')}/tx/{tx['hash']}",
        )
