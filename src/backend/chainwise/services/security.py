from typing import Literal

from chainwise.models import SecurityFinding

_Severity = Literal["high", "medium", "info"]

# Function-name -> (severity, description). Matched against the bare name
# (no signature, no args) of a decoded call, case-insensitively — deliberately
# name-based rather than selector-based: these are conventional Solidity
# names, not a standard, so this is a heuristic, not a guarantee (a contract
# could name a harmless function "upgradeTo"). Grounded in the decoded call
# itself, not the LLM's judgment, which is the point: an auditor gets a fact
# ("this call matches a known admin-function name"), not an opinion.
_NAME_PATTERNS: dict[str, tuple[_Severity, str]] = {
    "transferownership": ("high", "Transfers contract ownership to a new address."),
    "setowner": ("high", "Changes the contract's owner/admin address."),
    "renounceownership": ("high", "Permanently renounces contract ownership."),
    "upgradeto": ("high", "Upgrades the proxy's implementation contract."),
    "upgradetoandcall": ("high", "Upgrades the proxy's implementation and calls into it."),
    "setimplementation": ("high", "Changes the proxy's implementation contract."),
    "selfdestruct": ("high", "Destroys the contract and sends its balance to an address."),
    "grantrole": ("medium", "Grants a privileged role to an address."),
    "setadmin": ("medium", "Changes an admin-privileged address."),
}

# 2**256 - 1: the canonical "unlimited" ERC-20 allowance value.
_MAX_UINT256 = str(2**256 - 1)


def detect_risk_patterns(
    function_name: str | None, parameters: dict[str, str]
) -> list[SecurityFinding]:
    """Matches a decoded call's bare function name/parameters against known risky patterns.

    Deterministic and cheap (no I/O, no LLM) — called on every /explain
    request regardless of `mode`, unlike the mode/gas_tips prompt addenda.
    Returns [] when nothing matches or nothing was decoded, which is the
    common case and not itself suspicious.
    """
    if not function_name:
        return []

    findings: list[SecurityFinding] = []
    name = function_name.strip().lower()

    if pattern := _NAME_PATTERNS.get(name):
        severity, description = pattern
        findings.append(
            SecurityFinding(
                pattern=name,
                severity=severity,
                description=description,
                evidence=f"decoded function name: {function_name}",
            )
        )

    if name == "approve" and _MAX_UINT256 in parameters.values():
        findings.append(
            SecurityFinding(
                pattern="unlimited-approval",
                severity="medium",
                description="Grants an unlimited (max-uint256) token allowance.",
                evidence=f"approve() parameters: {parameters}",
            )
        )

    return findings
