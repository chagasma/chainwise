from typing import Any, Literal, Self

from pydantic import BaseModel

from chainwise.models import ExplanationMode, RepoGroundingResult, SecurityFinding, TokenMetadata

# Re-exported: routes.py imports ExplanationMode from here (it already imports
# the rest of this module), not from chainwise.models directly.
__all__ = ["ExplanationMode"]


def _nested(d: dict[str, Any] | None, key: str) -> Any | None:
    """`(d or {}).get(key)` — a field that's present but sometimes null in Blockscout's JSON."""
    return (d or {}).get(key)


def _revert_reason(raw: Any) -> str | None:
    """Blockscout sends `revert_reason` as a plain string for a `require`/`revert("msg")`,
    but as a decoded-object (`{"method_call": "CustomError()", ...}`) for a Solidity custom
    error — same shape as `decoded_input`. Normalize both to the string the LLM prompt expects.
    """
    if raw is None or isinstance(raw, str):
        return raw
    return raw.get("method_call") or raw.get("method_id")


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
    raw_input: str | None
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
            to_address=_nested(tx.get("to"), "hash"),
            value_wei=tx.get("value", "0"),
            gas_used=tx.get("gas_used"),
            fee_wei=_nested(tx.get("fee"), "value"),
            method=tx.get("method"),
            decoded_input=tx.get("decoded_input"),
            raw_input=tx.get("raw_input"),
            revert_reason=_revert_reason(tx.get("revert_reason")),
            logs=[
                LogEntry(
                    address=log["address"]["hash"],
                    event=_nested(log.get("decoded"), "method_call"),
                    decoded=log.get("decoded"),
                )
                for log in logs
            ],
            source_url=f"{explorer_url.rstrip('/')}/tx/{tx['hash']}",
        )


class LLMPromptPayload(BaseModel):
    """The transaction context sent to the LLM as one JSON blob (see agent/prompts.py)."""

    summary: TransactionSummary
    tokens: list[TokenMetadata]
    grounding: RepoGroundingResult | None
    security_findings: list[SecurityFinding]


class ExplanationResponse(BaseModel):
    """A natural-language explanation, grounded in the underlying transaction data."""

    summary: TransactionSummary
    tokens: list[TokenMetadata]
    grounding: RepoGroundingResult | None
    security_findings: list[SecurityFinding]
    explanation: str
    thread_id: str
    mode: ExplanationMode
    gas_tips: bool
