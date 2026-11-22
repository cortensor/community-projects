"""Structured OpenMinion @tool definitions for Cortensor builder release & triage."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import json
from pathlib import Path
import tomllib
from typing import Any, Callable

from openminion import tool

from src.kernel.event_bus import EventBus, redact_secrets, utc_now_iso


@dataclass(frozen=True)
class TriageToolset:
    """Bound OpenMinion @tool callables with zero sibling feature imports."""

    read_only_tools: tuple[Callable[..., str], ...]
    write_gated_tool: Callable[..., str]
    all_tools: tuple[Callable[..., str], ...]


def build_triage_toolset(
    *,
    workspace_root: Path,
    runtime_staging_dir: Path,
    bus: EventBus,
) -> TriageToolset:
    """Build workspace-confined OpenMinion @tool functions wired to EventBus."""
    resolved_root = workspace_root.resolve()
    resolved_staging = runtime_staging_dir.resolve()

    def _safe_subpath(rel_path: str) -> Path:
        cleaned = (rel_path or ".").strip() or "."
        candidate = (resolved_root / cleaned).resolve()
        if candidate != resolved_root and resolved_root not in candidate.parents:
            raise ValueError(f"Path '{rel_path}' escapes workspace root.")
        return candidate

    @tool(min_scope="READ_ONLY", idempotent=True)
    def inspect_workspace_manifest(workspace_rel_dir: str = ".") -> str:
        """Inspect pyproject.toml, .gitignore, and secret-hygiene posture in workspace_rel_dir."""
        target_dir = _safe_subpath(workspace_rel_dir)
        pyproject_path = resolved_root / "pyproject.toml"
        gitignore_path = resolved_root / ".gitignore"

        project_meta: dict[str, Any] = {}
        if pyproject_path.is_file():
            parsed = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
            proj = parsed.get("project") or {}
            project_meta = {
                "name": proj.get("name", "unknown"),
                "version": proj.get("version", "0.0.0"),
                "requires_python": proj.get("requires-python", ""),
                "dependencies": list(proj.get("dependencies") or []),
            }

        gitignore_entries = (
            [ln.strip() for ln in gitignore_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if gitignore_path.is_file()
            else []
        )
        env_leaks = [
            str(p.relative_to(resolved_root))
            for p in target_dir.rglob(".env*")
            if ".venv" not in p.parts and p.is_file()
        ]

        payload = {
            "inspected_dir": str(target_dir.relative_to(resolved_root)) if target_dir != resolved_root else ".",
            "project": project_meta,
            "gitignore_guards": gitignore_entries,
            "committed_env_files": env_leaks,
            "secret_hygiene_ok": len(env_leaks) == 0 and ".openminion_runtime/" in gitignore_entries,
        }
        rendered = json.dumps(payload, sort_keys=True)
        bus.publish(
            "tool.invoked",
            source_brick="triage_tools",
            payload={
                "tool_name": "inspect_workspace_manifest",
                "min_scope": "READ_ONLY",
                "idempotent": True,
                "arguments": {"workspace_rel_dir": workspace_rel_dir},
                "result_preview": redact_secrets(rendered[:280]),
            },
        )
        return rendered

    @tool(min_scope="READ_ONLY", idempotent=True)
    def audit_python_module_risks(target_subpath: str = "src") -> str:
        """Scan Python ASTs under target_subpath for sibling-import isolation and forbidden imports."""
        scan_root = _safe_subpath(target_subpath)
        py_files = sorted(
            p for p in scan_root.rglob("*.py") if "__pycache__" not in p.parts and ".venv" not in p.parts
        )
        sibling_violations: list[str] = []
        forbidden_imports: list[str] = []

        for py_file in py_files:
            rel = py_file.relative_to(resolved_root)
            parts = rel.parts
            own_feature = parts[2] if len(parts) >= 3 and parts[0] == "src" and parts[1] == "features" else None
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(rel))
            for node in ast.walk(tree):
                imported_mods: list[str] = []
                if isinstance(node, ast.Import):
                    imported_mods.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_mods.append(node.module)
                for mod in imported_mods:
                    if mod.startswith("unittest.mock") or mod in {"fastapi.testclient", "starlette.testclient"}:
                        forbidden_imports.append(f"{rel}:{mod}")
                    if own_feature and mod.startswith("src.features."):
                        target_feature = mod.split(".")[2]
                        if target_feature != own_feature:
                            sibling_violations.append(f"{rel}->{mod}")

        payload = {
            "scanned_subpath": str(scan_root.relative_to(resolved_root)) if scan_root != resolved_root else ".",
            "python_files_scanned": len(py_files),
            "sibling_import_violations": sibling_violations,
            "forbidden_mock_or_testclient_imports": forbidden_imports,
            "architecture_clean": len(sibling_violations) == 0 and len(forbidden_imports) == 0,
        }
        rendered = json.dumps(payload, sort_keys=True)
        bus.publish(
            "tool.invoked",
            source_brick="triage_tools",
            payload={
                "tool_name": "audit_python_module_risks",
                "min_scope": "READ_ONLY",
                "idempotent": True,
                "arguments": {"target_subpath": target_subpath},
                "result_preview": redact_secrets(rendered[:280]),
            },
        )
        return rendered

    @tool(min_scope="READ_ONLY", idempotent=True)
    def check_cortensor_config_posture(profile_mode: str = "cortensor-portal") -> str:
        """Evaluate OpenMinion 0.1.24 Cortensor Portal, Cortensor Router, and OpenAI-bridge config posture."""
        normalized = (profile_mode or "cortensor-portal").strip().lower()
        profiles: dict[str, dict[str, Any]] = {
            "cortensor-portal": {
                "catalog_id": "cortensor-portal",
                "agents_json_provider_key": "openai",
                "endpoint": "https://api.cortensor.app/v1",
                "credential_env": "CORTENSOR_API_KEY",
                "recommended_model": "oss-20b",
                "max_retries": 0,
                "retry_disabled_reason": "cortensor_portal_no_idempotency",
                "api_turn_timeout_floor_seconds": 45.0,
            },
            "cortensor-router": {
                "catalog_id": "cortensor-router",
                "agents_json_provider_key": "cortensor",
                "endpoint": "http://127.0.0.1:8080/api/v2/completions",
                "credential_env": "CORTENSOR_API_KEY",
                "recommended_model": "gpt-oss-20b",
                "max_retries": 0,
                "retry_disabled_reason": "cortensor_direct_single_attempt",
                "api_turn_timeout_floor_seconds": 455.0,
            },
            "gemini": {
                "catalog_id": "gemini",
                "agents_json_provider_key": "openai",
                "endpoint": "https://generativelanguage.googleapis.com/v1beta/openai",
                "credential_env": "GEMINI_API_KEY",
                "recommended_model": "gemini-2.5-flash",
                "max_retries": 2,
                "retry_disabled_reason": None,
                "api_turn_timeout_floor_seconds": 45.0,
            },
            "ollama-openai": {
                "catalog_id": "ollama",
                "agents_json_provider_key": "openai",
                "endpoint": "http://127.0.0.1:11434/v1",
                "credential_env": "MINIONBENCH_OLLAMA_KEY",
                "recommended_model": "qwen2.5:1.5b",
                "max_retries": 2,
                "retry_disabled_reason": None,
                "api_turn_timeout_floor_seconds": 45.0,
            },
        }
        selected = profiles.get(normalized, profiles["cortensor-portal"])
        payload = {
            "requested_profile": normalized,
            "selected_posture": selected,
            "agents_json_note": (
                "Always set agents.<id>.default_channel='console' and omit mismatched human display names "
                "in agents.<id>.name to avoid inbound_authenticity invalid_channel and UnknownProfileError."
            ),
        }
        rendered = json.dumps(payload, sort_keys=True)
        bus.publish(
            "tool.invoked",
            source_brick="triage_tools",
            payload={
                "tool_name": "check_cortensor_config_posture",
                "min_scope": "READ_ONLY",
                "idempotent": True,
                "arguments": {"profile_mode": profile_mode},
                "result_preview": redact_secrets(rendered[:280]),
            },
        )
        return rendered

    @tool
    def stage_release_brief(summary_line: str, readiness_verdict: str = "READY") -> str:
        """Write a policy-gated release triage brief inside .openminion_runtime/staged_release_brief.md."""
        resolved_staging.mkdir(parents=True, exist_ok=True)
        brief_path = resolved_staging / "staged_release_brief.md"
        safe_summary = redact_secrets(summary_line.strip())
        safe_verdict = redact_secrets(readiness_verdict.strip() or "READY")
        content = (
            f"# Staged Cortensor Release Brief\n\n"
            f"- **Timestamp (UTC):** `{utc_now_iso()}`\n"
            f"- **Verdict:** `{safe_verdict}`\n"
            f"- **Summary:** {safe_summary}\n"
        )
        brief_path.write_text(content, encoding="utf-8")
        payload = {
            "staged_path": str(brief_path),
            "verdict": safe_verdict,
            "bytes_written": len(content.encode("utf-8")),
        }
        rendered = json.dumps(payload, sort_keys=True)
        bus.publish(
            "tool.invoked",
            source_brick="triage_tools",
            payload={
                "tool_name": "stage_release_brief",
                "min_scope": "WRITE_CONFIRM",
                "idempotent": False,
                "arguments": {
                    "summary_line": safe_summary,
                    "readiness_verdict": safe_verdict,
                },
                "result_preview": redact_secrets(rendered[:280]),
            },
        )
        return rendered

    read_only = (
        inspect_workspace_manifest,
        audit_python_module_risks,
        check_cortensor_config_posture,
    )
    return TriageToolset(
        read_only_tools=read_only,
        write_gated_tool=stage_release_brief,
        all_tools=(*read_only, stage_release_brief),
    )
