from pydantic import BaseModel


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
