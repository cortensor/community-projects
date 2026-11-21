"""Portable OpenMinion MemoryBundle persistence and cross-run diffing."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openminion import MemoryBundle
from openminion.modules.memory.portability import (
    export_bundle,
    import_bundle,
    load_bundle,
    save_bundle,
)


def load_prior_check_ids(bundle_path: Path) -> list[str]:
    """Load check IDs recorded in the most recent portable MemoryBundle snapshot."""
    if not bundle_path.is_file():
        return []
    bundle = load_bundle(bundle_path)
    # Validate bundle trust posture before reading snapshot metadata.
    import_bundle(bundle, trust_mode="direct")
    raw_items: list[dict[str, Any]] = list(bundle.items)
    if not raw_items:
        return []
    latest = raw_items[-1]
    meta = latest.get("metadata") if isinstance(latest.get("metadata"), dict) else {}
    if isinstance(meta, dict) and isinstance(meta.get("blocker_ids"), list):
        return [str(x) for x in meta["blocker_ids"]]
    return []


def diff_findings(
    prior_ids: list[str], current_ids: list[str]
) -> tuple[list[str], list[str]]:
    """Return (resolved_since_last_run, persistent_from_last_run) sorted deterministically."""
    prior_set = set(prior_ids)
    current_set = set(current_ids)
    resolved = sorted(prior_set - current_set)
    persistent = sorted(prior_set & current_set)
    return resolved, persistent


def record_audit_memory(
    bundle_path: Path,
    *,
    target_path: str,
    decision: str,
    blocker_ids: list[str],
    warning_ids: list[str],
) -> MemoryBundle:
    """Append the current audit snapshot to a portable OpenMinion MemoryBundle file."""
    existing_items: list[dict[str, Any]] = []
    if bundle_path.is_file():
        prior_bundle = load_bundle(bundle_path)
        existing_items = list(prior_bundle.items)

    timestamp = datetime.now(UTC).isoformat()
    new_item: dict[str, Any] = {
        "id": f"audit-{len(existing_items) + 1}",
        "namespace": "release_gate",
        "record_type": "audit_snapshot",
        "content": (
            f"target={target_path} decision={decision} "
            f"blockers={','.join(blocker_ids) or 'none'}"
        ),
        "created_at": timestamp,
        "metadata": {
            "target_path": target_path,
            "decision": decision,
            "blocker_ids": list(blocker_ids),
            "warning_ids": list(warning_ids),
        },
    }
    bundle = export_bundle(
        [*existing_items, new_item],
        metadata={"app": "cortensor-release-gate", "updated_at": timestamp},
    )
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    save_bundle(bundle, bundle_path)
    return bundle
