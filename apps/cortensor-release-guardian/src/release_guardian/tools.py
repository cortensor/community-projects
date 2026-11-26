"""Read-only OpenMinion @tool definitions for auditing Cortensor / OpenMinion repositories."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from openminion import tool

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".openminion",
    "dist",
    "build",
}

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("OpenAI/Stripe-like secret key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GitHub personal access token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("AWS access key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Private key PEM block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "Hardcoded API key assignment",
        re.compile(r"""(?i)(?:api_key|secret_key|private_key)\s*[:=]\s*["'](?!env:|YOUR_|<|changeme|example)[A-Za-z0-9_\-]{16,}["']"""),
    ),
]


def _iter_repo_files(root: Path, max_files: int = 400) -> list[Path]:
    files: list[Path] = []
    if not root.exists():
        return files
    for item in sorted(root.rglob("*")):
        if len(files) >= max_files:
            break
        if any(part in IGNORED_DIRS for part in item.parts):
            continue
        if item.is_file():
            files.append(item)
    return files


@tool(min_scope="READ_ONLY", idempotent=True)
def scan_repo_structure(repo_path: str) -> str:
    """Inspect a repository for required release and Cortensor Hackathon #5 deliverables."""
    root = Path(repo_path).resolve()
    if not root.is_dir():
        return json.dumps({"ok": False, "error": f"Directory not found: {root}"})

    checks = {
        "has_readme": (root / "README.md").is_file(),
        "has_license": any((root / name).is_file() for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")),
        "has_pyproject_or_requirements": (root / "pyproject.toml").is_file()
        or (root / "requirements.txt").is_file(),
        "has_tests_dir": (root / "tests").is_dir(),
        "has_building_blocks_doc": (root / "docs" / "BUILDING_BLOCKS_TESTED.md").is_file(),
        "has_what_we_learned_doc": (root / "docs" / "WHAT_WE_LEARNED.md").is_file(),
        "has_openminion_config": any(
            p.name.endswith(".json") and "agent" in p.name.lower()
            for p in _iter_repo_files(root, max_files=200)
        ),
    }
    missing = [k for k, v in checks.items() if not v]
    py_count = sum(1 for p in _iter_repo_files(root) if p.suffix == ".py")
    result: dict[str, Any] = {
        "ok": True,
        "repo": str(root),
        "python_files": py_count,
        "checks": checks,
        "missing": missing,
    }
    return json.dumps(result, indent=2)


@tool(min_scope="READ_ONLY", idempotent=True)
def scan_secret_leaks(repo_path: str) -> str:
    """Scan repository files for accidental .env files or hardcoded credentials/secrets."""
    root = Path(repo_path).resolve()
    if not root.is_dir():
        return json.dumps({"ok": False, "error": f"Directory not found: {root}"})

    findings: list[dict[str, Any]] = []
    text_exts = {".py", ".json", ".yml", ".yaml", ".toml", ".md", ".txt", ".env", ".sh", ".ps1", ".js", ".ts"}

    for fpath in _iter_repo_files(root):
        rel = str(fpath.relative_to(root))
        if fpath.name == ".env" or (fpath.name.startswith(".env.") and not fpath.name.endswith(".example")):
            findings.append({"file": rel, "kind": "Committed .env file", "line": 1})
            continue
        if fpath.suffix.lower() not in text_exts or fpath.stat().st_size > 250_000:
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(content.splitlines(), start=1):
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append({"file": rel, "kind": label, "line": lineno})

    return json.dumps(
        {
            "ok": True,
            "clean": len(findings) == 0,
            "finding_count": len(findings),
            "findings": findings[:25],
        },
        indent=2,
    )


@tool(min_scope="READ_ONLY", idempotent=True)
def run_syntax_audit(repo_path: str) -> str:
    """Parse every Python source file with AST to catch syntax errors before release."""
    root = Path(repo_path).resolve()
    if not root.is_dir():
        return json.dumps({"ok": False, "error": f"Directory not found: {root}"})

    checked = 0
    errors: list[dict[str, Any]] = []
    for fpath in _iter_repo_files(root):
        if fpath.suffix != ".py":
            continue
        checked += 1
        try:
            source = fpath.read_text(encoding="utf-8")
            ast.parse(source, filename=str(fpath))
        except SyntaxError as exc:
            errors.append(
                {
                    "file": str(fpath.relative_to(root)),
                    "line": exc.lineno,
                    "message": exc.msg,
                }
            )

    return json.dumps(
        {
            "ok": True,
            "python_files_checked": checked,
            "syntax_clean": len(errors) == 0,
            "errors": errors,
        },
        indent=2,
    )


@tool(min_scope="READ_ONLY", idempotent=True)
def check_openminion_config(config_path: str) -> str:
    """Validate an OpenMinion agents.json configuration for safe action_policy and env-var credentials."""
    path = Path(config_path).resolve()
    if not path.is_file():
        return json.dumps({"ok": False, "error": f"Config file not found: {path}"})

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return json.dumps({"ok": False, "error": f"Invalid JSON: {exc}"})

    warnings: list[str] = []
    default_agent = data.get("default_agent")
    agents = data.get("agents", {})
    if not agents:
        warnings.append("No agents defined in config.")
    if default_agent and default_agent not in agents:
        warnings.append(f"default_agent '{default_agent}' not found in agents map.")

    policy = data.get("action_policy", {})
    if policy.get("mode") == "bypass":
        warnings.append("Top-level action_policy.mode is 'bypass'; prefer 'auto' with read-only allowance.")

    for aid, cfg in agents.items():
        api_key = str(cfg.get("api_key", ""))
        if api_key and not api_key.startswith("env:"):
            warnings.append(f"Agent '{aid}' has a literal api_key instead of 'env:VAR_NAME'.")
        if "permission_mode" in cfg:
            warnings.append(
                f"Agent '{aid}' sets unsupported field 'permission_mode' under agents.<id> (use action_policy)."
            )
        if not str(cfg.get("default_channel", "")).strip():
            warnings.append(
                f"Agent '{aid}' omits 'default_channel' (e.g. 'cli'); openminion 0.1.24 raises "
                f"'inbound authenticity denied (reason=invalid_channel)' on programmatic Agent.run()."
            )

    return json.dumps(
        {
            "ok": True,
            "config_path": str(path),
            "default_agent": default_agent,
            "agent_ids": list(agents.keys()),
            "safe": len(warnings) == 0,
            "warnings": warnings,
        },
        indent=2,
    )


ALL_TOOLS = [
    scan_repo_structure,
    scan_secret_leaks,
    run_syntax_audit,
    check_openminion_config,
]
