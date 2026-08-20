from chainwise.services.multi_tx import detect_relations

_Tx = tuple[str, str, str | None]


def test_detect_relations_returns_empty_for_unrelated_transactions() -> None:
    transactions: list[_Tx] = [
        ("0x1", "0xsenderA", "0xcontractA"),
        ("0x2", "0xsenderB", "0xcontractB"),
    ]

    assert detect_relations(transactions) == []


def test_detect_relations_flags_shared_sender() -> None:
    transactions: list[_Tx] = [
        ("0x1", "0xsame", "0xcontractA"),
        ("0x2", "0xsame", "0xcontractB"),
    ]

    relations = detect_relations(transactions)

    assert len(relations) == 1
    assert relations[0].kind == "shared_sender"
    assert relations[0].tx_hashes == ["0x1", "0x2"]


def test_detect_relations_flags_shared_counterparty() -> None:
    transactions: list[_Tx] = [
        ("0x1", "0xsenderA", "0xsame"),
        ("0x2", "0xsenderB", "0xsame"),
    ]

    relations = detect_relations(transactions)

    assert len(relations) == 1
    assert relations[0].kind == "shared_counterparty"
    assert relations[0].tx_hashes == ["0x1", "0x2"]


def test_detect_relations_ignores_null_counterparty() -> None:
    """A contract-creation tx has to_address=None — shouldn't group with other Nones."""
    transactions: list[_Tx] = [
        ("0x1", "0xsenderA", None),
        ("0x2", "0xsenderB", None),
    ]

    assert detect_relations(transactions) == []


def test_detect_relations_can_return_both_relation_kinds() -> None:
    transactions: list[_Tx] = [
        ("0x1", "0xsame", "0xalsosame"),
        ("0x2", "0xsame", "0xalsosame"),
    ]

    relations = detect_relations(transactions)

    assert {r.kind for r in relations} == {"shared_sender", "shared_counterparty"}
