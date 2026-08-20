from typing import Any, Literal

from pydantic import BaseModel

ExplanationMode = Literal["developer", "support", "auditor"]
"""Audience for a /tx/{hash}/explain response. Lives here (not api/schemas.py
or agent/prompts.py) so both layers can depend on it without either importing
the other — same reasoning as `TokenMetadata` below."""

DEFAULT_MODE: ExplanationMode = "developer"


class TokenMetadata(BaseModel):
    """ERC-20 metadata for a token seen transferring in a transaction's logs.

    Best-effort: `symbol`/`decimals` are null when the on-chain read call
    failed or the token doesn't follow the standard ABI. Lives here (not in
    api/schemas.py or services/enricher.py) so both layers can depend on it
    without either importing the other.
    """

    address: str
    symbol: str | None
    decimals: int | None


class DecodedCall(BaseModel):
    """A function call decoded against a specific ABI entry.

    `parameters` values are JSON-safe: ints are stringified (mirrors
    `TransactionSummary.value_wei` — avoids precision loss for uint256) and
    `bytes` become "0x"-prefixed hex.
    """

    function: str
    signature: str
    parameters: dict[str, Any]


class SecurityFinding(BaseModel):
    """A deterministic match against a known risky call pattern (not an LLM guess).

    Produced by `services/security.py` from the decoded method name/parameters
    only — grounded the same way `DecodedCall` is, so an "auditor"-mode
    explanation can cite it as fact rather than inference. Lives here (not in
    services/security.py or api/schemas.py) for the same cross-layer reason
    as `TokenMetadata`.
    """

    pattern: str
    severity: Literal["high", "medium", "info"]
    description: str
    evidence: str


class TransactionRelation(BaseModel):
    """A deterministic relationship detected between 2+ transactions being analyzed together.

    Produced by `services/multi_tx.py` from the transaction summaries only —
    same grounded-fact spirit as `SecurityFinding`, so a multi-transaction
    explanation can cite it instead of the LLM inventing a connection.
    """

    kind: str
    description: str
    tx_hashes: list[str]


class RepoGroundingResult(BaseModel):
    """A transaction's input decoded against an ABI artifact found in a configured repo.

    The fallback path of the network's `abi_strategy`: only produced when
    the explorer didn't already decode the call. `source_url` cites the
    exact file so the explanation can link to the real contract source.
    """

    repo: str
    file_path: str
    source_url: str
    decoded_call: DecodedCall
