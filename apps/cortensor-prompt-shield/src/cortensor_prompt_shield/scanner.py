"""Static AST @tool security scanner and OpenMinion agents.json policy auditor."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from .models import ConfigPolicyFinding, ToolSurfaceFinding

MUTATING_CALL_HINTS = {
    "write_text",
    "write_bytes",
    "unlink",
    "remove",
    "rmtree",
    "system",
    "popen",
    "run",
    "Popen",
    "check_output",
    "post",
    "put",
    "delete",
    "patch",
    "execute",
}

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), "Hardcoded OpenAI-style API key"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "Hardcoded GitHub PAT"),
    (re.compile(r"0x[a-fA-F0-9]{64}"), "Potential hardcoded 32-byte private key"),
]


def _extract_tool_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.AST | None:
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "tool":
            return dec
        if isinstance(dec, ast.Attribute) and dec.attr == "tool":
            return dec
        if isinstance(dec, ast.Call):
            fn = dec.func
            if (isinstance(fn, ast.Name) and fn.id == "tool") or (
                isinstance(fn, ast.Attribute) and fn.attr == "tool"
            ):
                return dec
    return None


def _decorator_kwargs(dec: ast.AST) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(dec, ast.Call):
        for kw in dec.keywords:
            if kw.arg is not None:
                try:
                    out[kw.arg] = ast.literal_eval(kw.value)
                except Exception:
                    out[kw.arg] = "<dynamic>"
    return out


def _body_mutating_calls(node: ast.AST) -> list[str]:
    hits: list[str] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            if isinstance(sub.func, ast.Attribute) and sub.func.attr in MUTATING_CALL_HINTS:
                hits.append(sub.func.attr)
            elif isinstance(sub.func, ast.Name) and sub.func.id in {"open", "eval", "exec"}:
                if sub.func.id in {"eval", "exec"}:
                    hits.append(sub.func.id)
                elif len(sub.args) >= 2:
                    try:
                        mode = ast.literal_eval(sub.args[1])
                        if isinstance(mode, str) and any(m in mode for m in ("w", "a", "+")):
                            hits.append(f"open({mode})")
                    except Exception:
                        pass
    return sorted(set(hits))


def scan_python_workspace(target_dir: str) -> list[ToolSurfaceFinding]:
    """Scan Python source files for OpenMinion @tool scope/safety misconfigurations."""

    root = Path(target_dir).resolve()
    findings: list[ToolSurfaceFinding] = []
    if not root.exists():
        return [
            ToolSurfaceFinding(
                file_path=str(root),
                function_name="<workspace>",
                line_number=1,
                severity="MEDIUM",
                rule_id="OM-PATH-001",
                detail="Target directory does not exist.",
                recommendation="Pass a valid Python workspace directory to --target.",
            )
        ]

    py_files = [root] if root.is_file() else sorted(root.rglob("*.py"))
    for py_file in py_files:
        if any(part in {".venv", "venv", "__pycache__", ".git", "node_modules"} for part in py_file.parts):
            continue
        try:
            source = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        rel = str(py_file.relative_to(root)) if root.is_dir() else py_file.name

        for pat, desc in SECRET_PATTERNS:
            for match in pat.finditer(source):
                line_no = source[: match.start()].count("\n") + 1
                findings.append(
                    ToolSurfaceFinding(
                        file_path=rel,
                        function_name="<module>",
                        line_number=line_no,
                        severity="HIGH",
                        rule_id="OM-SECRET-001",
                        detail=f"{desc} detected in source file.",
                        recommendation="Move credentials to environment variables referenced via agents.json api_key_env.",
                    )
                )

        try:
            tree = ast.parse(source, filename=rel)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            dec = _extract_tool_decorator(node)
            if dec is None:
                continue

            kwargs = _decorator_kwargs(dec)
            min_scope = kwargs.get("min_scope")
            dangerous = bool(kwargs.get("dangerous", False))
            mut_calls = _body_mutating_calls(node)

            if not min_scope:
                findings.append(
                    ToolSurfaceFinding(
                        file_path=rel,
                        function_name=node.name,
                        line_number=node.lineno,
                        severity="MEDIUM",
                        rule_id="OM-SCOPE-001",
                        detail=f"@tool '{node.name}' omits explicit min_scope (defaults to broad execution).",
                        recommendation='Annotate explicitly with @tool(min_scope="READ_ONLY", idempotent=True) or min_scope="WRITE_SAFE".',
                    )
                )

            if mut_calls and str(min_scope).upper() == "READ_ONLY":
                findings.append(
                    ToolSurfaceFinding(
                        file_path=rel,
                        function_name=node.name,
                        line_number=node.lineno,
                        severity="HIGH",
                        rule_id="OM-SCOPE-002",
                        detail=f"READ_ONLY @tool '{node.name}' invokes potentially mutating calls: {', '.join(mut_calls)}.",
                        recommendation='Upgrade to min_scope="WRITE_SAFE" and dangerous=True so action_policy enforces operator approval.',
                    )
                )
            elif mut_calls and not dangerous:
                findings.append(
                    ToolSurfaceFinding(
                        file_path=rel,
                        function_name=node.name,
                        line_number=node.lineno,
                        severity="MEDIUM",
                        rule_id="OM-DANGER-001",
                        detail=f"Mutating @tool '{node.name}' calls ({', '.join(mut_calls)}) without dangerous=True.",
                        recommendation="Set dangerous=True on side-effecting tools to require interactive approval_callback confirmation.",
                    )
                )

            if not ast.get_docstring(node):
                findings.append(
                    ToolSurfaceFinding(
                        file_path=rel,
                        function_name=node.name,
                        line_number=node.lineno,
                        severity="LOW",
                        rule_id="OM-DOC-001",
                        detail=f"@tool '{node.name}' is missing a docstring (weakens schema exposure & model routing).",
                        recommendation="Add a clear 1-sentence docstring stating exact inputs, constraints, and side effects.",
                    )
                )

    return findings


def audit_agents_config(config_path: str) -> list[ConfigPolicyFinding]:
    """Audit an OpenMinion agents.json file for least-privilege & Cortensor readiness."""

    path = Path(config_path)
    findings: list[ConfigPolicyFinding] = []
    if not path.exists():
        return [
            ConfigPolicyFinding(
                section="config",
                severity="MEDIUM",
                detail=f"Config file not found at {config_path}.",
                recommendation="Run `openminion config init` to generate a baseline agents.json.",
            )
        ]

    cfg = json.loads(path.read_text(encoding="utf-8"))

    ap = cfg.get("action_policy", {})
    if ap.get("default_action") != "require_confirm":
        findings.append(
            ConfigPolicyFinding(
                section="action_policy",
                severity="HIGH",
                detail=f"default_action is '{ap.get('default_action')}' instead of 'require_confirm'.",
                recommendation='Set action_policy.default_action = "require_confirm" so unapproved side effects fail closed.',
            )
        )

    sec = cfg.get("security", {}).get("tool_policy", {})
    if int(sec.get("max_calls_per_run", 999)) > 80:
        findings.append(
            ConfigPolicyFinding(
                section="security.tool_policy",
                severity="LOW",
                detail=f"max_calls_per_run is {sec.get('max_calls_per_run')} (high loop ceiling for untrusted inputs).",
                recommendation="Tighten security.tool_policy.max_calls_per_run <= 40 for production Cortensor workflows.",
            )
        )

    for prov_name, prov in (cfg.get("providers") or {}).items():
        if isinstance(prov, dict) and prov.get("api_key"):
            findings.append(
                ConfigPolicyFinding(
                    section=f"providers.{prov_name}",
                    severity="HIGH",
                    detail=f"Inline plaintext api_key found in providers.{prov_name}.",
                    recommendation="Keep api_key empty in agents.json and supply credentials only via api_key_env.",
                )
            )

    if not findings:
        findings.append(
            ConfigPolicyFinding(
                section="baseline",
                severity="INFO",
                detail="agents.json passes least-privilege checks (require_confirm enabled, zero inline secrets).",
                recommendation="Keep channel_authenticity.mode='strict' when exposing beyond localhost console.",
            )
        )

    return findings
