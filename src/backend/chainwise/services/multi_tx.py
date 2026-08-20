from collections import defaultdict

from chainwise.models import TransactionRelation


def detect_relations(
    transactions: list[tuple[str, str, str | None]],
) -> list[TransactionRelation]:
    """Deterministic relationships among a set of transactions analyzed together.
    Takes bare `(tx_hash, from_address, to_address)` tuples, not
    `TransactionSummary`, to stay independent of the api layer. [] means no
    shared sender/contract, not that the transactions are unrelated."""
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
