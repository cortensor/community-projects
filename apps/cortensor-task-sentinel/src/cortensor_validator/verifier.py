"""Static Code Safety and Syntax Verifier.
==========================================
Deterministic AST validator ensuring submitted code blocks are safe to execute.
Requires 0 LLM tokens and executes in <0.2ms.
"""

from __future__ import annotations

import ast
import time
from dataclasses import dataclass


FORBIDDEN_CALLS = frozenset({
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "input",
    "breakpoint",
    "getattr",
    "setattr",
    "delattr",
    "globals",
    "locals",
    "vars",
})

FORBIDDEN_MODULES = frozenset({
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "urllib",
    "requests",
    "httpx",
    "pty",
    "ctypes",
    "importlib",
    "pickle",
    "marshal",
    "shelve",
    "types",
})

FORBIDDEN_ATTRIBUTES = frozenset({
    "__subclasses__",
    "__bases__",
    "__class__",
    "__globals__",
    "__builtins__",
    "__dict__",
    "__code__",
    "__mro__",
    "__base__",
    "__getattribute__",
    "__reduce__",
    "__reduce_ex__",
    "gi_frame",
    "gi_code",
    "cr_frame",
    "ag_frame",
    "f_back",
    "f_globals",
    "f_locals",
    "f_builtins",
    "f_code",
    "tb_frame",
})


@dataclass(frozen=True, slots=True)
class SafetyCheckResult:
    """Result of static AST safety inspection."""

    valid: bool
    violations: tuple[str, ...] = ()
    ast_nodes_scanned: int = 0
    latency_ms: float = 0.0


def verify_code_safety(code_str: str) -> SafetyCheckResult:
    """Inspect Python code for unsafe primitives and syntax errors via AST.

    Parameters
    ----------
    code_str : str
        Python source code submitted by a miner.

    Returns
    -------
    SafetyCheckResult
        Inspection outcome with violations and latency.
    """
    t0 = time.perf_counter()
    violations: list[str] = []

    try:
        tree = ast.parse(code_str)
    except SyntaxError as err:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return SafetyCheckResult(
            valid=False,
            violations=(f"SyntaxError: {err.msg} at line {err.lineno}",),
            latency_ms=dt_ms,
        )

    nodes_scanned = 0
    for node in ast.walk(tree):
        nodes_scanned += 1

        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                if root_pkg in FORBIDDEN_MODULES:
                    violations.append(f"Forbidden import: '{alias.name}'")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                if root_pkg in FORBIDDEN_MODULES:
                    violations.append(f"Forbidden from-import: '{node.module}'")

        # Check function calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                violations.append(f"Forbidden builtin call: '{node.func.id}()'")

        # Check attribute access (sandbox escape defense)
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRIBUTES:
                violations.append(f"Forbidden attribute access: '{node.attr}'")

        # A format string can read attributes by name, so a dunder in any string is refused
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and "__" in node.value:
            violations.append("Forbidden dunder text in a string literal")

        # Check dangerous variable names
        elif isinstance(node, ast.Name):
            if node.id in {"__builtins__", "__import__", "importlib"}:
                violations.append(f"Forbidden variable access: '{node.id}'")

    dt_ms = (time.perf_counter() - t0) * 1000.0
    return SafetyCheckResult(
        valid=len(violations) == 0,
        violations=tuple(violations),
        ast_nodes_scanned=nodes_scanned,
        latency_ms=dt_ms,
    )
