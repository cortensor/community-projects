from __future__ import annotations

import re
from typing import Any

from openminion import MemoryBundle

from commitseam.ledger import QueueLedger

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]+"),
    re.compile(r"FAKE_SECRET_[A-Za-z0-9_\-]+"),
    re.compile(r"\b(?:sk|gsk|ghp|gho|xoxb|AIza)[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"\borg_[A-Za-z0-9]{10,}\b"),
    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    re.compile(r"(?i)(?:api[_-]?key|token|secret|password)\s*[=:]\s*['\"]?[^\s'\",;]+"),
    re.compile(r"/(?:Users|home)/[^/\s\"']+"),
)

_SENSITIVE_KEY_NAMES = frozenset({"api_key", "apikey", "authorization", "token", "secret", "password"})


def _redact_string(text: str) -> str:
    cleaned = text
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned


def redact_secrets(value: Any) -> Any:
    """Recursively scrub credentials, bearer tokens, synthetic secret markers, email PII, and local home paths."""
    def _walk(node: Any) -> Any:
        if isinstance(node, str):
            return _redact_string(node)
        if isinstance(node, dict):
            sanitized: dict[str, Any] = {}
            for k, v in node.items():
                key_str = str(k)
                safe_key = _redact_string(key_str)
                if key_str.lower() in _SENSITIVE_KEY_NAMES or safe_key != key_str:
                    sanitized[safe_key] = "[REDACTED]"
                else:
                    sanitized[safe_key] = _walk(v)
            return sanitized
        if isinstance(node, list):
            return [_walk(v) for v in node]
        if isinstance(node, tuple):
            return [_walk(v) for v in node]
        return node

    return _walk(value)


def export_memory_bundle(
    ledger: QueueLedger,
    *,
    request_id: str,
    mode: str,
    scenario: str | None = None,
) -> tuple[MemoryBundle, str]:
    """One-way read-only audit export from QueueLedger into a redacted OpenMinion MemoryBundle."""
    summary = ledger.reconcile(request_id)
    raw_items: list[dict[str, Any]] = []
    for job in summary["jobs"]:
        raw_items.append(
            {
                "kind": "rerun_job",
                "item_id": job["item_id"],
                "job_id": job["job_id"],
            }
        )
    for event in summary["events"]:
        raw_items.append(
            {
                "kind": "attempt_event",
                "item_id": event["item_id"],
                "fault_seam": event["fault_seam"],
                "result": event["result"],
                "job_id": event["job_id"],
                "error_code": event["error_code"],
            }
        )

    bundle_meta: dict[str, Any] = {
        "request_id": request_id,
        "mode": mode,
        "expected_count": summary["expected_count"],
        "committed_enqueue_count": summary["committed_enqueue_count"],
        "pending_count": len(summary["pending_item_ids"]),
        "exact_once_ok": summary["exact_once_ok"],
    }
    if scenario is not None:
        bundle_meta["scenario"] = scenario

    sanitized_items = redact_secrets(raw_items)
    sanitized_meta = redact_secrets(bundle_meta)
    bundle = MemoryBundle(items=sanitized_items, metadata=sanitized_meta)
    return bundle, bundle.to_json()
