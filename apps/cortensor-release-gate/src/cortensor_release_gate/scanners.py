"""Deterministic local repository scanners used by OpenMinion @tool wrappers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from cortensor_release_gate.models import (
    AuditFinding,
    CortensorWiringReport,
    DocsAuditReport,
    SecurityAuditReport,
)

SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "node_modules",
        ".openminion",
        "dist",
        "build",
        "out",
    }
)

TEXT_EXTENSIONS = frozenset(
    {
        ".py",
        ".md",
        ".yml",
        ".yaml",
        ".toml",
        ".json",
        ".txt",
        ".env",
        ".sh",
        ".ps1",
        ".ts",
        ".js",
    }
)

REQUIRED_COMMUNITY_FILES = (
    "PROJECTS.yml",
    "README.md",
    "STATUS.md",
    "RELEASE.md",
    "LICENSE",
)

SECRET_RULES: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "SEC-PEM-KEY",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "Private key block committed in repository.",
    ),
    (
        "SEC-OPENAI-KEY",
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        "API key pattern detected; replace with environment variable lookup.",
    ),
    (
        "SEC-GH-TOKEN",
        re.compile(r"\b(?:ghp|gho|github_pat)_[A-Za-z0-9_]{20,}\b"),
        "GitHub personal access token pattern detected.",
    ),
    (
        "SEC-HEX-PRIVKEY",
        re.compile(
            r"(?i)(?:private_key|priv_key|wallet_key)\s*[:=]\s*['\"]?(?:0x)?[0-9a-f]{64}['\"]?"
        ),
        "Hexadecimal private key assignment detected.",
    ),
)

CORTENSOR_URL_PATTERN = re.compile(
    r"https?://[^\s'\"`)]*(?:cortensor\.app|cortensor\.network|/api/v[123]/completions)[^\s'\"`)]*"
)
OPENMINION_PIN_PATTERN = re.compile(r"openminion\s*([=<>!~]=?\s*[0-9]+\.[0-9]+(?:\.[0-9]+)?)")
PLACEHOLDER_OWNER_PATTERN = re.compile(r"@your-github-handle|@example|TODO", re.IGNORECASE)


def _iter_repo_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(repo_root).parts):
            continue
        files.append(path)
    return files


def _read_text_safe(path: Path, max_bytes: int = 256_000) -> str | None:
    if path.stat().st_size > max_bytes:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def scan_repository_security(repo_root: Path) -> SecurityAuditReport:
    """Scan repository files for committed secrets and unignored .env files."""
    resolved_root = repo_root.resolve()
    files = _iter_repo_files(resolved_root)
    findings: list[AuditFinding] = []
    scanned_count = 0

    for path in files:
        rel_path = path.relative_to(resolved_root).as_posix()
        if path.name == ".env":
            findings.append(
                AuditFinding(
                    check_id="SEC-DOTENV-FILE",
                    category="security",
                    severity="high",
                    path=rel_path,
                    message="Tracked or local .env file present in repository root.",
                    remediation="Keep secrets in local untracked .env and commit .env.example only.",
                )
            )
            continue

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        content = _read_text_safe(path)
        if content is None:
            continue
        scanned_count += 1

        for check_id, pattern, message in SECRET_RULES:
            if pattern.search(content):
                findings.append(
                    AuditFinding(
                        check_id=check_id,
                        category="security",
                        severity="critical",
                        path=rel_path,
                        message=message,
                        remediation="Remove credential literal and load it from environment variables.",
                    )
                )

    passed = not any(item.severity in {"critical", "high"} for item in findings)
    summary = (
        f"Scanned {scanned_count} text files; found {len(findings)} security issue(s)."
    )
    return SecurityAuditReport(
        passed=passed,
        files_scanned=scanned_count,
        findings=findings,
        summary=summary,
    )


def _validate_projects_yml(repo_root: Path) -> list[AuditFinding]:
    projects_file = repo_root / "PROJECTS.yml"
    if not projects_file.is_file():
        return []
    raw = _read_text_safe(projects_file)
    if raw is None:
        return [
            AuditFinding(
                check_id="DOC-PROJECTS-UNREADABLE",
                category="docs",
                severity="high",
                path="PROJECTS.yml",
                message="Could not decode PROJECTS.yml as UTF-8.",
                remediation="Save PROJECTS.yml as valid UTF-8 YAML.",
            )
        ]
    try:
        parsed: Any = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return [
            AuditFinding(
                check_id="DOC-PROJECTS-YAML",
                category="docs",
                severity="high",
                path="PROJECTS.yml",
                message=f"Invalid YAML syntax in PROJECTS.yml: {exc}",
                remediation="Fix YAML syntax to match cortensor/community-projects schema.",
            )
        ]

    entries = parsed if isinstance(parsed, list) else [parsed] if isinstance(parsed, dict) else []
    if not entries or not isinstance(entries[0], dict):
        return [
            AuditFinding(
                check_id="DOC-PROJECTS-SCHEMA",
                category="docs",
                severity="high",
                path="PROJECTS.yml",
                message="PROJECTS.yml must contain a project entry mapping.",
                remediation="Define name, category, owner, status, created, version, and tags.",
            )
        ]

    findings: list[AuditFinding] = []
    entry = entries[0]
    for required_key in ("name", "category", "owner", "status", "version"):
        if not entry.get(required_key):
            findings.append(
                AuditFinding(
                    check_id=f"DOC-PROJECTS-MISSING-{required_key.upper()}",
                    category="docs",
                    severity="medium",
                    path="PROJECTS.yml",
                    message=f"PROJECTS.yml is missing required field '{required_key}'.",
                    remediation=f"Populate '{required_key}' in PROJECTS.yml.",
                )
            )
    owner_val = str(entry.get("owner") or "")
    if PLACEHOLDER_OWNER_PATTERN.search(owner_val):
        findings.append(
            AuditFinding(
                check_id="DOC-PROJECTS-PLACEHOLDER-OWNER",
                category="docs",
                severity="low",
                path="PROJECTS.yml",
                message=f"PROJECTS.yml owner '{owner_val}' looks like a template placeholder.",
                remediation="Replace placeholder owner with your GitHub handle before opening a PR.",
            )
        )
    return findings


def scan_repository_docs(repo_root: Path) -> DocsAuditReport:
    """Verify required Cortensor community-projects files and Hackathon #5 notes."""
    resolved_root = repo_root.resolve()
    present_files: list[str] = []
    missing_files: list[str] = []
    findings: list[AuditFinding] = []

    for filename in REQUIRED_COMMUNITY_FILES:
        candidate = resolved_root / filename
        if candidate.is_file() and candidate.stat().st_size > 0:
            present_files.append(filename)
        else:
            missing_files.append(filename)
            findings.append(
                AuditFinding(
                    check_id=f"DOC-MISSING-{filename.replace('.', '_').upper()}",
                    category="docs",
                    severity="high",
                    path=filename,
                    message=f"Required submission file '{filename}' is missing or empty.",
                    remediation=f"Create non-empty '{filename}' following cortensor/community-projects guidelines.",
                )
            )

    findings.extend(_validate_projects_yml(resolved_root))

    readme_path = resolved_root / "README.md"
    if readme_path.is_file():
        readme_text = _read_text_safe(readme_path) or ""
        if "openminion" not in readme_text.lower():
            findings.append(
                AuditFinding(
                    check_id="DOC-README-OPENMINION",
                    category="docs",
                    severity="medium",
                    path="README.md",
                    message="README.md does not document the OpenMinion SDK workflow.",
                    remediation="Add setup, run commands, and OpenMinion workflow explanation to README.md.",
                )
            )

    has_feedback_notes = any(
        (resolved_root / rel).is_file()
        for rel in (
            "docs/BUILDING_BLOCKS_TESTED.md",
            "docs/WHAT_WE_LEARNED.md",
            "FEEDBACK.md",
            "BUILDING_BLOCKS_TESTED.md",
        )
    )
    if not has_feedback_notes:
        findings.append(
            AuditFinding(
                check_id="DOC-HACKATHON5-NOTES",
                category="docs",
                severity="medium",
                path="docs/",
                message="Missing Building Blocks Tested / What We Learned feedback documentation.",
                remediation="Add docs/BUILDING_BLOCKS_TESTED.md and docs/WHAT_WE_LEARNED.md.",
            )
        )

    passed = not missing_files and not any(
        item.severity in {"critical", "high"} for item in findings
    )
    summary = (
        f"{len(present_files)}/{len(REQUIRED_COMMUNITY_FILES)} required community files present; "
        f"{len(findings)} documentation finding(s)."
    )
    return DocsAuditReport(
        passed=passed,
        present_files=present_files,
        missing_files=missing_files,
        findings=findings,
        summary=summary,
    )


def scan_cortensor_wiring(repo_root: Path) -> CortensorWiringReport:
    """Inspect dependency pins, OpenMinion imports, Cortensor endpoints, and test files."""
    resolved_root = repo_root.resolve()
    files = _iter_repo_files(resolved_root)
    uses_openminion = False
    openminion_pin: str | None = None
    endpoints: set[str] = set()
    has_tests = False
    findings: list[AuditFinding] = []

    for path in files:
        rel_path = path.relative_to(resolved_root).as_posix()
        if rel_path.startswith("tests/") and path.name.startswith("test_") and path.suffix == ".py":
            has_tests = True

        if path.name in {"pyproject.toml", "requirements.txt"}:
            dep_text = _read_text_safe(path) or ""
            match = OPENMINION_PIN_PATTERN.search(dep_text)
            if match:
                openminion_pin = match.group(1).strip()

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        content = _read_text_safe(path) or ""
        if path.suffix == ".py" and "openminion" in content:
            uses_openminion = True
        for url in CORTENSOR_URL_PATTERN.findall(content):
            endpoints.add(url)

    if not uses_openminion:
        findings.append(
            AuditFinding(
                check_id="WIRE-NO-OPENMINION",
                category="cortensor",
                severity="critical",
                path="src/",
                message="No Python module imports openminion.",
                remediation="Use openminion 0.1.x SDK (Agent, APIRuntime, @tool, subagent, Handoff).",
            )
        )
    if openminion_pin is None:
        findings.append(
            AuditFinding(
                check_id="WIRE-UNPINNED-OPENMINION",
                category="packaging",
                severity="medium",
                path="pyproject.toml",
                message="openminion dependency pin was not found in pyproject.toml or requirements.txt.",
                remediation="Pin openminion==0.1.23 (or >=0.1.21) for reproducible setup.",
            )
        )
    if not has_tests:
        findings.append(
            AuditFinding(
                check_id="WIRE-NO-TESTS",
                category="packaging",
                severity="medium",
                path="tests/",
                message="No test_*.py files found under tests/.",
                remediation="Add unit and OpenMinion integration tests under tests/.",
            )
        )

    return CortensorWiringReport(
        uses_openminion=uses_openminion,
        openminion_pin=openminion_pin,
        cortensor_endpoints_detected=sorted(endpoints),
        has_tests=has_tests,
        findings=findings,
    )
