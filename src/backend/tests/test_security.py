from chainwise.services.security import detect_risk_patterns

MAX_UINT256 = str(2**256 - 1)


def test_detect_risk_patterns_returns_empty_for_no_function_name() -> None:
    assert detect_risk_patterns(None, {}) == []


def test_detect_risk_patterns_returns_empty_for_ordinary_call() -> None:
    assert detect_risk_patterns("transfer", {"to": "0xabc", "value": "1000"}) == []


def test_detect_risk_patterns_flags_ownership_transfer() -> None:
    findings = detect_risk_patterns("transferOwnership", {"newOwner": "0xabc"})

    assert len(findings) == 1
    assert findings[0].pattern == "transferownership"
    assert findings[0].severity == "high"
    assert "0xabc" not in findings[0].description  # description is generic, not per-call


def test_detect_risk_patterns_is_case_insensitive() -> None:
    findings = detect_risk_patterns("UpgradeTo", {"newImplementation": "0xdef"})

    assert len(findings) == 1
    assert findings[0].pattern == "upgradeto"


def test_detect_risk_patterns_flags_unlimited_approval() -> None:
    findings = detect_risk_patterns("approve", {"spender": "0xabc", "value": MAX_UINT256})

    assert len(findings) == 1
    assert findings[0].pattern == "unlimited-approval"
    assert findings[0].severity == "medium"


def test_detect_risk_patterns_does_not_flag_bounded_approval() -> None:
    findings = detect_risk_patterns("approve", {"spender": "0xabc", "value": "1000"})

    assert findings == []
