from collections import defaultdict

from chainwise.models import TransactionRelation


def detect_relations(
    transactions: list[tuple[str, str, str | None]],
) -> list[TransactionRelation]:
    """Deterministic relationships among a set of transactions being analyzed together.

    `transactions` is a list of `(tx_hash, from_address, to_address)` —
    primitives, not `TransactionSummary`, so this stays independent of the
    api layer (mirrors `services/security.py` taking a bare function name
    instead of a `TransactionSummary`). Cheap (no I/O, no LLM): a fact the
    LLM can cite, not something it has to spot itself. Returns [] when no
    pattern matched, which doesn't mean the transactions are unrelated —
    only that they don't share a sender or a called contract.
    """
    by_sender: dict[str, list[str]] = defaultdict(list)
    by_counterparty: dict[str, list[str]] = defaultdict(list)
    for tx_hash, from_address, to_address in transactions:
        by_sender[from_address].append(tx_hash)
        if to_address:
            by_counterparty[to_address].append(tx_hash)

    relations = []
    for address, hashes in by_sender.items():
        if len(hashes) > 1:
            relations.append(
                TransactionRelation(
                    kind="shared_sender",
                    description=f"All sent from the same address: {address}.",
                    tx_hashes=hashes,
                )
            )
    for address, hashes in by_counterparty.items():
        if len(hashes) > 1:
            relations.append(
                TransactionRelation(
                    kind="shared_counterparty",
                    description=f"All call the same contract: {address}.",
                    tx_hashes=hashes,
                )
            )
    return relations
