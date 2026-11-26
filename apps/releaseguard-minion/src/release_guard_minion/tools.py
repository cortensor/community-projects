"""Risk-tiered OpenMinion @tool definitions for repository release auditing."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from openminion import tool

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{24,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "private_key_pem",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    ),
    (
        "evm_private_key",
        re.compile(
            r"(?i)(?:private[_-]?key|mnemonic)\s*[:=]\s*['\"]?(?:0x)?[0-9a-f]{64}\b"
        ),
    ),
)

_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
        "target",
    }
)


def _resolve_repo_dir(repo_path: str) -> Path:
    root = Path(repo_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Repository directory does not exist: {repo_path}")
    return root


def _git_output(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


@tool(
    name="inspect_repo_manifest",
    min_scope="READ_ONLY",
    idempotent=True,
    tags=("release_guard", "manifest"),
)
def inspect_repo_manifest(repo_path: str) -> str:
    """Inspect README, LICENSE, CHANGELOG, SECURITY, package manifests, and git state."""

    root = _resolve_repo_dir(repo_path)
    entries = {p.name.lower(): p.name for p in root.iterdir()}

    docs_present = {
        "readme": any(k.startswith("readme") for k in entries),
        "license": any(k.startswith("license") or k.startswith("copying") for k in entries),
        "changelog": any(k.startswith("changelog") for k in entries),
        "security": "security.md" in entries,
        "gitignore": ".gitignore" in entries,
    }
    manifests = [
        entries[name]
        for name in (
            "pyproject.toml",
            "package.json",
            "cargo.toml",
            "foundry.toml",
            "go.mod",
            "hardhat.config.ts",
            "hardhat.config.js",
        )
        if name in entries
    ]

    is_git = (root / ".git").exists()
    branch = _git_output(root, "rev-parse", "--abbrev-ref", "HEAD") if is_git else None
    dirty_raw = _git_output(root, "status", "--porcelain") if is_git else None
    tags_raw = _git_output(root, "tag", "--sort=-creatordate") if is_git else None
    recent_tags = [t for t in (tags_raw or "").splitlines() if t][:5]

    payload: dict[str, Any] = {
        "repo_name": root.name,
        "docs_present": docs_present,
        "manifests": manifests,
        "is_git_repo": is_git,
        "branch": branch,
        "dirty_files_count": len(dirty_raw.splitlines()) if dirty_raw else 0,
        "recent_tags": recent_tags,
    }
    return json.dumps(payload, sort_keys=True)


@tool(
    name="inspect_ci_and_tests",
    min_scope="READ_ONLY",
    idempotent=True,
    tags=("release_guard", "ci"),
)
def inspect_ci_and_tests(repo_path: str) -> str:
    """Inspect CI workflows, test directories, and build/test automation files."""

    root = _resolve_repo_dir(repo_path)
    workflows_dir = root / ".github" / "workflows"
    workflows: list[str] = []
    if workflows_dir.is_dir():
        workflows = sorted(
            p.name
            for p in workflows_dir.iterdir()
            if p.is_file() and p.suffix in {".yml", ".yaml"}
        )

    test_dirs = [
        name
        for name in ("tests", "test", "__tests__", "spec")
        if (root / name).is_dir()
    ]
    test_file_count = 0
    for dirname in test_dirs:
        for candidate in (root / dirname).rglob("*"):
            if candidate.is_file() and (
                candidate.name.startswith("test_")
                or ".test." in candidate.name
                or ".spec." in candidate.name
                or candidate.name.endswith("_test.py")
                or candidate.name.endswith(".t.sol")
            ):
                test_file_count += 1

    automation = [
        name
        for name in ("Makefile", "justfile", "tox.ini", "pytest.ini", ".pre-commit-config.yaml")
        if (root / name).is_file()
    ]
    payload = {
        "repo_name": root.name,
        "ci_workflows": workflows,
        "test_dirs": test_dirs,
        "test_file_count": test_file_count,
        "automation_files": automation,
    }
    return json.dumps(payload, sort_keys=True)


@tool(
    name="scan_secret_hygiene",
    min_scope="READ_ONLY",
    idempotent=True,
    tags=("release_guard", "security"),
)
def scan_secret_hygiene(repo_path: str, max_files: int = 200) -> str:
    """Scan repository files for hardcoded secrets, private keys, and exposed .env files."""

    root = _resolve_repo_dir(repo_path)
    env_files: list[str] = []
    findings: list[dict[str, Any]] = []
    scanned = 0

    for path in sorted(root.rglob("*")):
        if any(part in _IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if not path.is_file():
            continue
        rel = str(path.relative_to(root))
        if path.name == ".env" or (
            path.name.startswith(".env.")
            and not path.name.endswith((".example", ".sample", ".template"))
        ):
            env_files.append(rel)
        if scanned >= max_files:
            continue
        if path.stat().st_size > 256_000:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        for rule_name, pattern in _SECRET_PATTERNS:
            if pattern.search(content):
                findings.append({"file": rel, "rule": rule_name})

    gitignore_text = ""
    gitignore = root / ".gitignore"
    if gitignore.is_file():
        gitignore_text = gitignore.read_text(encoding="utf-8", errors="ignore")

    payload = {
        "repo_name": root.name,
        "files_scanned": scanned,
        "env_files_present": env_files,
        "gitignore_covers_env": ".env" in gitignore_text,
        "secret_findings": findings,
        "clean": not env_files and not findings,
    }
    return json.dumps(payload, sort_keys=True)


@tool(
    name="write_release_brief",
    idempotent=True,
    tags=("release_guard", "artifact"),
)
def write_release_brief(output_path: str, brief_markdown: str) -> str:
    """Write a Markdown release readiness brief to disk (WRITE_SAFE; policy-gated)."""

    target = Path(output_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(brief_markdown, encoding="utf-8")
    return json.dumps(
        {"written_path": str(target), "bytes": len(brief_markdown.encode("utf-8"))},
        sort_keys=True,
    )


@tool(
    name="create_release_tag",
    dangerous=True,
    tags=("release_guard", "git", "release"),
)
def create_release_tag(repo_path: str, tag_name: str, message: str) -> str:
    """Create an annotated git tag in the repository (DANGEROUS; denied unless approved)."""

    root = _resolve_repo_dir(repo_path)
    if not re.fullmatch(r"v?[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9._-]+)?", tag_name):
        raise ValueError(f"Invalid semantic release tag: {tag_name!r}")
    proc = subprocess.run(
        ["git", "tag", "-a", tag_name, "-m", message],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git tag failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return json.dumps({"repo": root.name, "tag_created": tag_name}, sort_keys=True)
