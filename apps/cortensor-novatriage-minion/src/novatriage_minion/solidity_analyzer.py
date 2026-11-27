"""Deterministic local Solidity static security analyzer."""

from __future__ import annotations

import re
from pathlib import Path

from .models import RiskTier, SolidityAuditResult, SolidityFinding


_SEVERITY_WEIGHTS: dict[str, int] = {
    "CRITICAL": 30,
    "HIGH": 20,
    "MEDIUM": 10,
    "LOW": 5,
    "INFO": 1,
}

_SIMPLE_PATTERNS: tuple[tuple[str, str, str, re.Pattern[str], str], ...] = (
    (
        "TX_ORIGIN_AUTH",
        "HIGH",
        "Authorization relies on tx.origin",
        re.compile(r"\btx\.origin\b"),
        "Replace tx.origin checks with msg.sender or EIP-712 signatures to prevent phishing relay attacks.",
    ),
    (
        "UNTRUSTED_DELEGATECALL",
        "CRITICAL",
        "Low-level delegatecall execution detected",
        re.compile(r"\.\s*delegatecall\s*\("),
        "Restrict delegatecall to immutable trusted implementation addresses or remove arbitrary target execution.",
    ),
    (
        "SELFDESTRUCT_PRESENT",
        "HIGH",
        "selfdestruct opcode present in contract",
        re.compile(r"\b(?:selfdestruct|suicide)\s*\("),
        "Remove selfdestruct (deprecated post-Cancun) and use pausable withdrawal flows instead.",
    ),
    (
        "BLACKLIST_HOOK",
        "MEDIUM",
        "Centralized address blacklist / freeze mapping detected",
        re.compile(r"\b(?:setBlacklist|blacklist|frozen|isBlacklisted)\b", re.IGNORECASE),
        "Document freeze privileges clearly, gate behind timelocked multisig, and emit governance events.",
    ),
    (
        "OWNER_DRAIN_HOOK",
        "HIGH",
        "Privileged emergencyWithdraw / sweep balance drain function detected",
        re.compile(r"\bfunction\s+(?:emergencyWithdraw|sweep|withdrawAll|rugPull)\b"),
        "Enforce timelocks, multisig governance, and user-fund accounting guards so admins cannot drain user deposits.",
    ),
)

_CALL_RE = re.compile(r"\.\s*call(?:\s*\{[^}]*\})?\s*\(")
_CALL_CHECKED_RE = re.compile(r"\(\s*bool\s+(\w+)\s*,")
_STATE_WRITE_RE = re.compile(
    r"\b(?:balances|shares|deposits|userBalance|allowance)\s*\[[^\]]+\]\s*(?:[-+]?=)|"
    r"\btotalSupply\s*(?:[-+]?=)|"
    r"\b(?:balances|shares|deposits)\s*\[[^\]]+\]\s*=\s*0\b"
)
_MINT_CALL_RE = re.compile(r"\b_mint\s*\(")
_FUNCTION_DEF_RE = re.compile(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)(.*)")
_PRAGMA_RE = re.compile(r"pragma\s+solidity\s+([^;]+);")


def _strip_comments(line: str) -> str:
    idx = line.find("//")
    return line[:idx] if idx != -1 else line


def _risk_tier(score: int) -> RiskTier:
    if score >= 75:
        return "CRITICAL"
    if score >= 45:
        return "HIGH"
    if score >= 20:
        return "MEDIUM"
    if score > 0:
        return "LOW"
    return "MINIMAL"


def _analyze_function_blocks(lines: list[str]) -> list[SolidityFinding]:
    """Scan function bodies for reentrancy, unchecked low-level calls, and unguarded mint."""
    findings: list[SolidityFinding] = []
    n = len(lines)
    i = 0
    while i < n:
        clean = _strip_comments(lines[i])
        fn_match = _FUNCTION_DEF_RE.search(clean)
        if not fn_match:
            i += 1
            continue

        fn_name = fn_match.group(1)
        fn_header = clean
        start_idx = i
        brace_depth = clean.count("{") - clean.count("}")
        j = i
        while brace_depth == 0 and j + 1 < n and ";" not in _strip_comments(lines[j]):
            j += 1
            nxt = _strip_comments(lines[j])
            fn_header += " " + nxt
            brace_depth += nxt.count("{") - nxt.count("}")

        if brace_depth <= 0:
            i += 1
            continue

        body_lines: list[tuple[int, str]] = []
        while j + 1 < n and brace_depth > 0:
            j += 1
            body_clean = _strip_comments(lines[j])
            brace_depth += body_clean.count("{") - body_clean.count("}")
            body_lines.append((j + 1, body_clean))

        has_nonreentrant = "nonreentrant" in fn_header.lower()
        has_access_guard = bool(
            re.search(
                r"\b(?:onlyOwner|onlyRole|onlyAdmin|onlyGovernance|onlyMinter|require\s*\(\s*msg\.sender\s*==)\b",
                fn_header,
            )
            or any("msg.sender ==" in b or "onlyOwner" in b for _, b in body_lines)
        )

        call_line: int | None = None
        call_snippet = ""
        checked_var: str | None = None
        var_checked_in_require = False

        for line_no, body_line in body_lines:
            if _CALL_RE.search(body_line):
                if call_line is None:
                    call_line = line_no
                    call_snippet = lines[line_no - 1].strip()
                checked = _CALL_CHECKED_RE.search(body_line)
                if checked:
                    checked_var = checked.group(1)
                else:
                    findings.append(
                        SolidityFinding(
                            rule_id="UNCHECKED_LOW_LEVEL_CALL",
                            severity="HIGH",
                            title=f"Unchecked low-level call return value in {fn_name}()",
                            line=line_no,
                            snippet=lines[line_no - 1].strip(),
                            remediation="Capture `(bool ok, ) = ...` and revert when `!ok`.",
                        )
                    )
                continue

            if checked_var and re.search(rf"\b(?:require|if)\s*\([^)]*\b{re.escape(checked_var)}\b", body_line):
                var_checked_in_require = True

            if call_line is not None and not has_nonreentrant and _STATE_WRITE_RE.search(body_line):
                findings.append(
                    SolidityFinding(
                        rule_id="REENTRANCY_BEFORE_WRITE",
                        severity="CRITICAL",
                        title=f"State mutation after external call in {fn_name}() (reentrancy)",
                        line=call_line,
                        snippet=f"{call_snippet} ... -> line {line_no}: {lines[line_no - 1].strip()}",
                        remediation="Follow Checks-Effects-Interactions: update balances/state before external .call and add nonReentrant.",
                    )
                )
                call_line = None

            if (
                _MINT_CALL_RE.search(body_line)
                and fn_name != "constructor"
                and not fn_name.startswith("_")
                and not has_access_guard
            ):
                findings.append(
                    SolidityFinding(
                        rule_id="ARBITRARY_MINT",
                        severity="CRITICAL",
                        title=f"Unguarded token _mint() reachable via public function {fn_name}()",
                        line=line_no,
                        snippet=lines[line_no - 1].strip(),
                        remediation="Restrict minting to constructor or a capped, role-gated mint controller.",
                    )
                )

        if checked_var and not var_checked_in_require:
            findings.append(
                SolidityFinding(
                    rule_id="UNCHECKED_LOW_LEVEL_CALL",
                    severity="HIGH",
                    title=f"Captured call boolean `{checked_var}` is never checked in {fn_name}()",
                    line=call_line or (start_idx + 1),
                    snippet=call_snippet or lines[start_idx].strip(),
                    remediation=f"Check `require({checked_var}, \"Call failed\")` or revert on `!{checked_var}`.",
                )
            )

        i = j + 1
    return findings


def analyze_solidity_source(
    *,
    source_code: str = "",
    file_path: str = "",
    contract_label: str = "",
) -> SolidityAuditResult:
    """Run deterministic static checks on Solidity code from inline text or a file path."""
    if not source_code and file_path:
        path = Path(file_path).expanduser()
        source_code = path.read_text(encoding="utf-8")
        if not contract_label:
            contract_label = path.name
    if not source_code.strip():
        raise ValueError("Provide non-empty `source_code` or a readable `file_path`.")

    label = contract_label or "inline_contract.sol"
    lines = source_code.splitlines()
    findings: list[SolidityFinding] = []

    for idx, raw_line in enumerate(lines, start=1):
        clean = _strip_comments(raw_line)
        if not clean.strip():
            continue
        for rule_id, severity, title, pattern, remediation in _SIMPLE_PATTERNS:
            if pattern.search(clean):
                findings.append(
                    SolidityFinding(
                        rule_id=rule_id,
                        severity=severity,  # type: ignore[arg-type]
                        title=title,
                        line=idx,
                        snippet=raw_line.strip(),
                        remediation=remediation,
                    )
                )
        pragma_match = _PRAGMA_RE.search(clean)
        if pragma_match:
            constraint = pragma_match.group(1).strip()
            if constraint.startswith("^") or "<0.8" in constraint:
                findings.append(
                    SolidityFinding(
                        rule_id="FLOATING_OR_LEGACY_PRAGMA",
                        severity="LOW",
                        title=f"Floating or legacy Solidity compiler pragma ({constraint})",
                        line=idx,
                        snippet=raw_line.strip(),
                        remediation="Pin an explicit Solidity >=0.8.20 compiler version for deterministic builds.",
                    )
                )

    findings.extend(_analyze_function_blocks(lines))
    findings.sort(key=lambda item: (item.line, item.rule_id))

    raw_score = sum(_SEVERITY_WEIGHTS.get(item.severity, 0) for item in findings)
    score = min(100, raw_score)
    return SolidityAuditResult(
        contract_label=label,
        lines_scanned=len(lines),
        risk_score=score,
        risk_tier=_risk_tier(score),
        finding_count=len(findings),
        findings=findings,
    )
