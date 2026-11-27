"""OpenMinion 0.1 Skills, MemoryBundle, Tasks, Sessions, and Diagnostics integration."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from openminion import APIRuntime, MemoryBundle
from openminion.api.operations.tasks import execute_task_control
from openminion.api.queries.tasks import build_task_surface
from openminion.modules.memory.portability import (
    export_bundle,
    import_bundle,
    load_bundle,
    save_bundle,
)
from openminion.modules.skill.interfaces import SkillIngestAuthority
from openminion.modules.skill.runtime.skill import Skill
from openminion.modules.task.surface import resolve_task_surface_source

from .models import NovaTriageReport


def setup_novatriage_skill(
    *,
    skill_markdown_path: Path,
    home_root: Path,
    known_tools: list[str],
    agent_id: str = "default",
) -> dict[str, Any]:
    """Ingest, admit as verified, match, and render the NovaTriage Skill package."""
    ctl = Skill(
        {"ingest_enabled": True},
        home_root=home_root,
        known_tools=known_tools,
    )
    try:
        authority = SkillIngestAuthority.local_operator(
            surface="novatriage.setup",
            principal_id="novatriage-operator",
            source_kind="local",
        )
        markdown = skill_markdown_path.read_text(encoding="utf-8")
        skill_id, version_hash, warnings = ctl.ingest_text(
            name="novatriage-solidity-audit",
            markdown=markdown,
            scope="global",
            agent_id=agent_id,
            promotion_path="operator",
            authority=authority,
        )
        state = ctl.get_skill_version_state(skill_id=skill_id, version_hash=version_hash)
        if state is None or state.get("admission_state") != "active":
            ctl.admit_skill_version(
                skill_id=skill_id,
                version_hash=version_hash,
                expected_active_version_hash=state.get("active_version_hash") if state else None,
                target_status="verified",
                reason="Verified NovaTriage Solidity & x402 triage playbook",
                authority=authority,
            )
        matches = ctl.match(
            intent_text="audit solidity contract and verify x402 challenge",
            step_hint={"step": "static_analysis"},
            agent_id=agent_id,
            k=3,
        )
        snippet_text, _ = ctl.render_snippet(
            skill_id=skill_id,
            version_hash=version_hash,
            purpose="act",
            max_tokens=300,
        )
        return {
            "skill_id": skill_id,
            "version_hash": version_hash,
            "warnings": list(warnings),
            "matched_ids": [m.skill_id for m in matches],
            "snippet_preview": snippet_text[:240],
        }
    finally:
        ctl.close()


def persist_triage_memory_bundle(
    *,
    report: NovaTriageReport,
    bundle_path: Path,
) -> dict[str, Any]:
    """Persist and validate a triage verdict inside a portable OpenMinion MemoryBundle."""
    existing_items: list[dict[str, Any]] = []
    if bundle_path.exists():
        existing_items = list(load_bundle(bundle_path).items)

    record = {
        "kind": "novatriage_verdict",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "target_name": report.target_name,
        "risk_score": report.overall_risk_score,
        "risk_tier": report.overall_risk_tier,
        "recommendation": report.recommendation,
        "finding_rules": [f.rule_id for f in report.solidity_audit.findings],
        "x402_pay_to": report.x402_probe.pay_to if report.x402_probe else "",
    }
    bundle: MemoryBundle = export_bundle(
        [*existing_items, record],
        metadata={"app": "cortensor-novatriage-minion", "schema": "v1"},
    )
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    save_bundle(bundle, bundle_path)
    reloaded = load_bundle(bundle_path)
    receipt = import_bundle(reloaded, trust_mode="direct")
    return {
        "bundle_path": str(bundle_path),
        "bundle_version": reloaded.version,
        "item_count": len(reloaded.items),
        "import_receipt": receipt,
    }


def schedule_watchlist_task(
    runtime: APIRuntime,
    *,
    target_label: str,
    token_address: str = "",
    session_id: str = "novatriage-watchlist",
) -> dict[str, Any]:
    """Schedule and inspect a recurring watchlist re-triage task via OpenMinion task controls."""
    instruction = f"Re-run NovaTriage watchlist check for {target_label}"
    if token_address:
        instruction += f" ({token_address})"
    created = execute_task_control(
        runtime=runtime,
        tool_name="task.schedule",
        arguments={
            "name": f"watchlist-{target_label}",
            "instruction": instruction,
            "schedule": {"kind": "every", "hours": 24},
        },
        agent_id="default",
        session_id=session_id,
        request_id="novatriage-task-schedule-1",
    )
    owner = resolve_task_surface_source(runtime)
    surface = build_task_surface(owner, agent_id="default", session_id=session_id)
    tasks = surface.list_tasks(runs_limit=5)
    return {
        "created": created,
        "visible_task_count": len(tasks),
        "tasks": tasks,
    }


def collect_runtime_diagnostics(runtime: APIRuntime) -> dict[str, Any]:
    """Export real OpenMinion APIRuntime posture, self-model, capability, and tool inventory."""
    posture = runtime.runtime_posture()
    self_model = runtime.runtime_self_model()
    capabilities = runtime.capability_report()
    inventory = runtime.tool_inventory_report()
    return {
        "runtime_mode": posture.get("runtime_mode"),
        "brain_bridge_active": posture.get("brain_bridge_active"),
        "canonical_turn_path": posture.get("canonical_turn_path"),
        "self_model_agent_id": self_model.get("agent_id"),
        "self_model_sections": sorted(self_model.get("sections", {}).keys())
        if isinstance(self_model.get("sections"), dict)
        else sorted(self_model.keys()),
        "selected_provider": (capabilities.get("providers") or {}).get("selected"),
        "tool_inventory_count": len(inventory),
        "sample_tools": [item.get("name") for item in inventory[:12]],
        "session_db_exists": (Path(runtime.data_root) / "state" / "openminion.db").exists()
        or any(Path(runtime.home_root).rglob("*.db")),
    }
