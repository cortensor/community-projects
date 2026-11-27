"""Deterministic repository and endpoint audit tools for ProofAudit Minion."""

from __future__ import annotations

import ast
import json
import py_compile
import re
import time
from pathlib import Path
from typing import Any

import httpx
from openminion import tool

_SKIP_DIRS = {".venv", "venv", ".git", "__pycache__", ".openminion", "node_modules", ".pytest_cache"}
_TEXT_EXTS = {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".env", ".cfg", ".ini"}

_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OpenRouter key", re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}")),
    ("OpenAI key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{24,}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
)

_FORBIDDEN_LABEL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile("\x41I[\x20-]generated", re.IGNORECASE),
    re.compile("\x41I\\s*\u751f\u6210"),
)

_SDK_SYMBOLS = (
    "APIRuntime",
    "Agent",
    "ProviderError",
    "AgentOutputValidationError",
    "TurnTimeoutError",
)


def _iter_repo_files(root: Path, *, suffix: str | None = None, limit: int = 400) -> list[Path]:
    files: list[Path] = []
    if not root.exists() or not root.is_dir():
        return files
    for path in sorted(root.rglob("*")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if suffix is not None and path.suffix.lower() != suffix:
            continue
        files.append(path)
        if len(files) >= limit:
            break
    return files


@tool(min_scope="READ_ONLY", idempotent=True)
def inspect_repo_manifest(repo_path: str) -> str:
    """Verify LICENSE, README, requirements pin, .gitignore, and scan for secrets."""
    root = Path(repo_path).resolve()
    findings: list[dict[str, str]] = []

    if not root.exists() or not root.is_dir():
        return json.dumps(
            {
                "repo_path": str(root),
                "repo_name": root.name,
                "ok": False,
                "findings": [
                    {
                        "check_id": "manifest.repo_exists",
                        "category": "manifest",
                        "status": "FAIL",
                        "evidence": f"Directory not found: {root}",
                        "fix": "Provide a valid local repository directory path.",
                    }
                ],
            },
            indent=2,
        )

    # 1. LICENSE check (MIT or Apache-2.0)
    license_file = root / "LICENSE"
    if not license_file.exists():
        license_file = root / "LICENSE.md"
    if license_file.exists():
        lic_text = license_file.read_text(encoding="utf-8", errors="ignore").lower()
        if "mit license" in lic_text or "permission is hereby granted, free of charge" in lic_text:
            findings.append(
                {
                    "check_id": "manifest.license",
                    "category": "manifest",
                    "status": "PASS",
                    "evidence": f"{license_file.name} present (MIT License detected).",
                    "fix": "",
                }
            )
        elif "apache license" in lic_text:
            findings.append(
                {
                    "check_id": "manifest.license",
                    "category": "manifest",
                    "status": "PASS",
                    "evidence": f"{license_file.name} present (Apache-2.0 License detected).",
                    "fix": "",
                }
            )
        else:
            findings.append(
                {
                    "check_id": "manifest.license",
                    "category": "manifest",
                    "status": "WARN",
                    "evidence": f"{license_file.name} exists but MIT/Apache-2.0 text was not recognized.",
                    "fix": "Use standard MIT or Apache-2.0 license text in LICENSE.",
                }
            )
    else:
        findings.append(
            {
                "check_id": "manifest.license",
                "category": "manifest",
                "status": "FAIL",
                "evidence": "Missing LICENSE file at repository root.",
                "fix": "Add a standard MIT LICENSE file at the repository root.",
            }
        )

    # 2. README.md check
    readme_file = root / "README.md"
    if readme_file.exists() and readme_file.stat().st_size >= 80:
        findings.append(
            {
                "check_id": "manifest.readme",
                "category": "manifest",
                "status": "PASS",
                "evidence": f"README.md present ({readme_file.stat().st_size} bytes).",
                "fix": "",
            }
        )
    elif readme_file.exists():
        findings.append(
            {
                "check_id": "manifest.readme",
                "category": "manifest",
                "status": "WARN",
                "evidence": f"README.md is very short ({readme_file.stat().st_size} bytes).",
                "fix": "Expand README.md with setup, run commands, and architecture overview.",
            }
        )
    else:
        findings.append(
            {
                "check_id": "manifest.readme",
                "category": "manifest",
                "status": "FAIL",
                "evidence": "Missing README.md at repository root.",
                "fix": "Add README.md documenting installation, usage, and OpenMinion integration.",
            }
        )

    # 3. requirements.txt / openminion== pin check
    req_file = root / "requirements.txt"
    pyproject_file = root / "pyproject.toml"
    pin_found = False
    pin_evidence = ""
    if req_file.exists():
        req_text = req_file.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"(?im)^openminion==([^\s#]+)", req_text)
        if match:
            pin_found = True
            pin_evidence = f"requirements.txt pins openminion=={match.group(1)}."
        elif "openminion" in req_text.lower():
            pin_evidence = "requirements.txt lists openminion without an exact == pin."
        else:
            pin_evidence = "requirements.txt does not list openminion."
    elif pyproject_file.exists():
        pyp_text = pyproject_file.read_text(encoding="utf-8", errors="ignore")
        if "openminion==" in pyp_text:
            pin_found = True
            pin_evidence = "pyproject.toml pins openminion==."
        else:
            pin_evidence = "pyproject.toml exists without exact openminion== pin."
    else:
        pin_evidence = "Missing requirements.txt and pyproject.toml."

    if pin_found:
        findings.append(
            {
                "check_id": "manifest.openminion_pin",
                "category": "manifest",
                "status": "PASS",
                "evidence": pin_evidence,
                "fix": "",
            }
        )
    else:
        findings.append(
            {
                "check_id": "manifest.openminion_pin",
                "category": "manifest",
                "status": "FAIL",
                "evidence": pin_evidence,
                "fix": "Pin openminion==0.1.24 in requirements.txt.",
            }
        )

    # 4. .gitignore check
    gitignore_file = root / ".gitignore"
    if gitignore_file.exists():
        gi_text = gitignore_file.read_text(encoding="utf-8", errors="ignore")
        missing_entries = [e for e in (".venv", "__pycache__", ".openminion", ".env") if e not in gi_text]
        if not missing_entries:
            findings.append(
                {
                    "check_id": "manifest.gitignore",
                    "category": "manifest",
                    "status": "PASS",
                    "evidence": ".gitignore covers .venv, __pycache__, .openminion, and .env.",
                    "fix": "",
                }
            )
        else:
            findings.append(
                {
                    "check_id": "manifest.gitignore",
                    "category": "manifest",
                    "status": "WARN",
                    "evidence": f".gitignore missing recommended entries: {', '.join(missing_entries)}.",
                    "fix": f"Add {', '.join(missing_entries)} to .gitignore.",
                }
            )
    else:
        findings.append(
            {
                "check_id": "manifest.gitignore",
                "category": "manifest",
                "status": "WARN",
                "evidence": "Missing .gitignore at repository root.",
                "fix": "Add .gitignore excluding .venv/, __pycache__/, .openminion/, *.pyc, and .env.",
            }
        )

    # 5. Secret & hygiene scan
    secret_hits: list[str] = []
    label_hits: list[str] = []
    for file_path in _iter_repo_files(root):
        if file_path.suffix.lower() not in _TEXT_EXTS and file_path.name not in {"LICENSE", ".gitignore"}:
            continue
        if file_path.name == ".env":
            continue
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        rel = str(file_path.relative_to(root))
        for label, pattern in _SECRET_PATTERNS:
            if pattern.search(content):
                secret_hits.append(f"{rel} ({label})")
        for pat in _FORBIDDEN_LABEL_PATTERNS:
            if pat.search(content):
                label_hits.append(rel)

    if secret_hits:
        findings.append(
            {
                "check_id": "manifest.secrets_hygiene",
                "category": "manifest",
                "status": "FAIL",
                "evidence": f"Potential secret material detected in: {', '.join(secret_hits[:5])}.",
                "fix": "Remove hardcoded secrets and read credentials from environment variables.",
            }
        )
    elif label_hits:
        findings.append(
            {
                "check_id": "manifest.secrets_hygiene",
                "category": "manifest",
                "status": "WARN",
                "evidence": f"Attribution label detected in: {', '.join(label_hits[:5])}.",
                "fix": "Remove boilerplate attribution labels from repository files.",
            }
        )
    else:
        findings.append(
            {
                "check_id": "manifest.secrets_hygiene",
                "category": "manifest",
                "status": "PASS",
                "evidence": "No hardcoded secrets or disallowed labels detected in scanned repository files.",
                "fix": "",
            }
        )

    has_fail = any(item["status"] == "FAIL" for item in findings)
    return json.dumps(
        {
            "repo_path": str(root),
            "repo_name": root.name,
            "ok": not has_fail,
            "findings": findings,
        },
        indent=2,
    )


@tool(min_scope="READ_ONLY", idempotent=True)
def scan_sdk_surface(repo_path: str) -> str:
    """Use Python AST to detect real OpenMinion SDK building blocks used in the repo."""
    root = Path(repo_path).resolve()
    py_files = _iter_repo_files(root, suffix=".py")
    detected: set[str] = set()
    per_file: list[dict[str, Any]] = []

    for py_file in py_files:
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        rel = str(py_file.relative_to(root))
        file_blocks: set[str] = set()

        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError:
            continue

        has_openminion_import = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "openminion" or alias.name.startswith("openminion."):
                        has_openminion_import = True
            elif isinstance(node, ast.ImportFrom):
                if node.module and (node.module == "openminion" or node.module.startswith("openminion.")):
                    has_openminion_import = True
                    for alias in node.names:
                        if alias.name in _SDK_SYMBOLS:
                            file_blocks.add(alias.name)
                        elif alias.name == "tool":
                            file_blocks.add("@tool")
            elif isinstance(node, ast.Name) and node.id in _SDK_SYMBOLS and has_openminion_import:
                file_blocks.add(node.id)
            elif isinstance(node, ast.FunctionDef):
                for dec in node.decorator_list:
                    dec_name = ""
                    if isinstance(dec, ast.Name):
                        dec_name = dec.id
                    elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                        dec_name = dec.func.id
                    elif isinstance(dec, ast.Attribute):
                        dec_name = dec.attr
                    elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        dec_name = dec.func.attr
                    if dec_name == "tool":
                        file_blocks.add("@tool")
            elif isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg in {"output_type", "session_id", "approval_callback"}:
                        file_blocks.add(kw.arg)

        if file_blocks:
            detected.update(file_blocks)
            per_file.append({"file": rel, "blocks": sorted(file_blocks)})

    # Also check README / docs / scripts for openminion CLI/doctor mentions
    for doc_file in _iter_repo_files(root):
        if doc_file.suffix.lower() not in {".md", ".py", ".sh", ".ps1", ".txt"}:
            continue
        doc_text = doc_file.read_text(encoding="utf-8", errors="ignore")
        if "openminion doctor" in doc_text or "openminion setup" in doc_text:
            detected.add("openminion CLI/doctor")
            break

    blocks_list = sorted(detected)
    if len(blocks_list) >= 3:
        finding = {
            "check_id": "sdk.surface_coverage",
            "category": "sdk",
            "status": "PASS",
            "evidence": f"Detected {len(blocks_list)} OpenMinion building blocks across {len(py_files)} Python files: {', '.join(blocks_list)}.",
            "fix": "",
        }
    elif blocks_list:
        finding = {
            "check_id": "sdk.surface_coverage",
            "category": "sdk",
            "status": "WARN",
            "evidence": f"Limited OpenMinion surface detected ({', '.join(blocks_list)}).",
            "fix": "Exercise APIRuntime, Agent, @tool, output_type, session_id, approval_callback, and ProviderError.",
        }
    else:
        finding = {
            "check_id": "sdk.surface_coverage",
            "category": "sdk",
            "status": "FAIL",
            "evidence": "No OpenMinion SDK building blocks detected via AST scan.",
            "fix": "Integrate openminion APIRuntime, Agent, and @tool in Python source files.",
        }

    return json.dumps(
        {
            "repo_path": str(root),
            "files_scanned": len(py_files),
            "building_blocks_detected": blocks_list,
            "per_file": per_file,
            "finding": finding,
        },
        indent=2,
    )


@tool(min_scope="READ_ONLY", idempotent=True)
def probe_openai_compatible_endpoint(base_url: str) -> str:
    """Perform a safe read-only HTTP reachability probe against an OpenAI-compatible endpoint."""
    cleaned = base_url.strip().rstrip("/")
    if not cleaned:
        return json.dumps(
            {
                "base_url": base_url,
                "reachable": False,
                "status_code": None,
                "latency_ms": None,
                "error": "Empty base_url",
                "finding": {
                    "check_id": "endpoint.reachability",
                    "category": "endpoint",
                    "status": "WARN",
                    "evidence": "No endpoint URL provided for reachability probe.",
                    "fix": "Pass --base-url or select a provider with a configured endpoint.",
                },
            },
            indent=2,
        )

    probe_url = cleaned if cleaned.endswith("/models") else f"{cleaned}/models"
    started = time.perf_counter()
    status_code: int | None = None
    error_msg = ""
    reachable = False

    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            resp = client.get(probe_url)
            status_code = resp.status_code
            if status_code == 404 and probe_url != cleaned:
                resp = client.get(cleaned)
                status_code = resp.status_code
                probe_url = cleaned
            reachable = status_code < 500
    except httpx.HTTPError as exc:
        error_msg = f"{type(exc).__name__}: {exc}"

    latency_ms = round((time.perf_counter() - started) * 1000.0, 2)

    if reachable:
        finding = {
            "check_id": "endpoint.reachability",
            "category": "endpoint",
            "status": "PASS",
            "evidence": f"Endpoint {probe_url} responded with HTTP {status_code} in {latency_ms} ms.",
            "fix": "",
        }
    else:
        finding = {
            "check_id": "endpoint.reachability",
            "category": "endpoint",
            "status": "WARN",
            "evidence": f"Endpoint {probe_url} unreachable ({error_msg or f'HTTP {status_code}'}) in {latency_ms} ms.",
            "fix": "Verify network connectivity, endpoint URL, or run against a live OpenRouter/Cortensor endpoint.",
        }

    return json.dumps(
        {
            "base_url": cleaned,
            "probed_url": probe_url,
            "reachable": reachable,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "error": error_msg,
            "finding": finding,
        },
        indent=2,
    )


@tool(idempotent=True)
def run_repo_smoke_check(repo_path: str) -> str:
    """Run bounded Python py_compile across .py files without executing untrusted code."""
    root = Path(repo_path).resolve()
    py_files = _iter_repo_files(root, suffix=".py", limit=200)
    errors: list[dict[str, str]] = []
    compiled_count = 0

    for py_file in py_files:
        try:
            py_compile.compile(str(py_file), doraise=True)
            compiled_count += 1
        except py_compile.PyCompileError as exc:
            errors.append({"file": str(py_file.relative_to(root)), "error": str(exc)})

    if not py_files:
        finding = {
            "check_id": "smoke.py_compile",
            "category": "smoke",
            "status": "WARN",
            "evidence": f"No Python files found under {root}.",
            "fix": "Ensure the target repository contains Python source files.",
        }
    elif errors:
        finding = {
            "check_id": "smoke.py_compile",
            "category": "smoke",
            "status": "FAIL",
            "evidence": f"py_compile failed on {len(errors)}/{len(py_files)} files: {errors[0]['file']}.",
            "fix": "Fix Python syntax errors reported by py_compile.",
        }
    else:
        finding = {
            "check_id": "smoke.py_compile",
            "category": "smoke",
            "status": "PASS",
            "evidence": f"py_compile succeeded on all {compiled_count} Python files.",
            "fix": "",
        }

    return json.dumps(
        {
            "repo_path": str(root),
            "files_checked": len(py_files),
            "compiled_count": compiled_count,
            "errors": errors,
            "finding": finding,
        },
        indent=2,
    )
