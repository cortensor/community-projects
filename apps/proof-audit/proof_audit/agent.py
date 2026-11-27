"""Two-stage ProofAudit Minion workflow backed by OpenMinion APIRuntime and Agent."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from openminion import (
    APIRuntime,
    Agent,
    AgentOutputValidationError,
    ProviderError,
    TurnTimeoutError,
)
from openminion.services.bootstrap.provider_setup import (
    ProviderSetupRequest,
    atomic_save_setup_config,
    build_provider_setup,
)

from proof_audit.checks import (
    inspect_repo_manifest,
    probe_openai_compatible_endpoint,
    run_repo_smoke_check,
    scan_sdk_surface,
)
from proof_audit.models import CheckFinding, ProofAuditReport

DEFAULT_MODELS: dict[str, str] = {
    "openrouter": "openai/gpt-4.1-mini",
    "cortensor-portal": "oss-20b",
    "cortensor-router": "gpt-oss-20b",
    "custom-openai-compatible": "model-id",
}

DEFAULT_ENDPOINTS: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "cortensor-portal": "https://api.cortensor.app/v1",
    "cortensor-router": "http://127.0.0.1:8080/api/v2/completions",
}


@dataclass
class AuditRunOutcome:
    """Result bundle returned by :func:`run_proof_audit`."""

    report: ProofAuditReport
    facts: dict[str, Any]
    session_id: str
    approvals: list[dict[str, Any]] = field(default_factory=list)
    used_offline_fallback: bool = False
    provider_error: str | None = None
    out_dir: Path | None = None


def build_isolated_runtime_config(
    *,
    work_dir: Path,
    provider: str,
    model: str | None = None,
    base_url: str | None = None,
) -> Path:
    """Create an isolated OpenMinion agents.json for the requested provider."""
    resolved_model = (model or "").strip() or DEFAULT_MODELS.get(provider, "model-id")
    resolved_base_url = (base_url or "").strip() or DEFAULT_ENDPOINTS.get(provider, "")
    cfg_path = work_dir / "agents.json"

    request = ProviderSetupRequest(
        preset_id=provider,
        agent_id="default",
        model=resolved_model,
        base_url=resolved_base_url,
        config_path=str(cfg_path),
        home_root=work_dir,
        data_root=work_dir,
        env=dict(os.environ),
    )
    setup_result = build_provider_setup(request)
    atomic_save_setup_config(setup_result.config, cfg_path)
    return cfg_path


def collect_deterministic_facts(repo_path: str, probe_url: str) -> dict[str, Any]:
    """Run all 4 deterministic checks directly to guarantee complete ground-truth facts."""
    manifest_raw = inspect_repo_manifest(repo_path)
    sdk_raw = scan_sdk_surface(repo_path)
    endpoint_raw = probe_openai_compatible_endpoint(probe_url)
    smoke_raw = run_repo_smoke_check(repo_path)

    return {
        "manifest": json.loads(manifest_raw),
        "sdk": json.loads(sdk_raw),
        "endpoint": json.loads(endpoint_raw),
        "smoke": json.loads(smoke_raw),
    }


def build_offline_report(repo_path: str, facts: dict[str, Any], *, note: str = "") -> ProofAuditReport:
    """Build a deterministic ProofAuditReport from collected tool facts."""
    root = Path(repo_path).resolve()
    findings: list[CheckFinding] = []

    for item in facts.get("manifest", {}).get("findings", []):
        findings.append(CheckFinding(**item))

    for section in ("sdk", "endpoint", "smoke"):
        finding_data = facts.get(section, {}).get("finding")
        if isinstance(finding_data, dict):
            findings.append(CheckFinding(**finding_data))

    blocks = list(facts.get("sdk", {}).get("building_blocks_detected", []))
    fail_count = sum(1 for f in findings if f.status == "FAIL")
    warn_count = sum(1 for f in findings if f.status == "WARN")

    score = max(0, 100 - (fail_count * 25) - (warn_count * 10))
    if fail_count > 0:
        verdict = "BLOCKED"
    elif warn_count > 0:
        verdict = "WARNINGS"
    else:
        verdict = "READY"

    remediation_steps = [f.fix for f in findings if f.status in {"WARN", "FAIL"} and f.fix]
    summary = (
        f"Audited {root.name}: {verdict} (score {score}/100) with "
        f"{len(findings) - fail_count - warn_count} PASS, {warn_count} WARN, {fail_count} FAIL."
    )
    if note:
        summary = f"{summary} ({note})"

    return ProofAuditReport(
        repo_name=root.name,
        verdict=verdict,
        score=score,
        building_blocks_detected=blocks,
        findings=findings,
        remediation_steps=remediation_steps,
        summary=summary,
    )


def render_report_markdown(report: ProofAuditReport, outcome: AuditRunOutcome) -> str:
    """Render a clean Markdown report from ProofAuditReport."""
    lines = [
        f"# ProofAudit Report: `{report.repo_name}`",
        "",
        f"- **Verdict**: `{report.verdict}`",
        f"- **Score**: `{report.score}/100`",
        f"- **Session ID**: `{outcome.session_id}`",
        f"- **Offline Fallback**: `{outcome.used_offline_fallback}`",
        "",
        "## Executive Summary",
        "",
        report.summary,
        "",
        "## OpenMinion Building Blocks Detected",
        "",
    ]
    if report.building_blocks_detected:
        for block in report.building_blocks_detected:
            lines.append(f"- `{block}`")
    else:
        lines.append("- None detected")

    lines.extend(
        [
            "",
            "## Check Findings",
            "",
            "| Check ID | Category | Status | Evidence | Fix |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for finding in report.findings:
        evidence = finding.evidence.replace("|", "\\|")
        fix = (finding.fix or "-").replace("|", "\\|")
        lines.append(
            f"| `{finding.check_id}` | {finding.category} | **{finding.status}** | {evidence} | {fix} |"
        )

    lines.extend(["", "## Remediation Steps", ""])
    if report.remediation_steps:
        for idx, step in enumerate(report.remediation_steps, start=1):
            lines.append(f"{idx}. {step}")
    else:
        lines.append("No remediation required.")

    return "\n".join(lines) + "\n"


def write_audit_artifacts(
    *,
    out_dir: Path,
    outcome: AuditRunOutcome,
    provider: str,
    model: str,
    base_url: str,
) -> None:
    """Write facts.json, report.md, and run.txt into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    facts_payload = {
        "repo_name": outcome.report.repo_name,
        "session_id": outcome.session_id,
        "approvals": outcome.approvals,
        "used_offline_fallback": outcome.used_offline_fallback,
        "provider_error": outcome.provider_error,
        "facts": outcome.facts,
        "report": outcome.report.model_dump(),
    }
    (out_dir / "facts.json").write_text(json.dumps(facts_payload, indent=2), encoding="utf-8")
    (out_dir / "report.md").write_text(render_report_markdown(outcome.report, outcome), encoding="utf-8")

    run_lines = [
        f"timestamp_utc={datetime.now(timezone.utc).isoformat()}",
        f"provider={provider}",
        f"model={model}",
        f"base_url={base_url}",
        f"session_id={outcome.session_id}",
        f"approvals_count={len(outcome.approvals)}",
        f"approvals={json.dumps(outcome.approvals)}",
        f"used_offline_fallback={outcome.used_offline_fallback}",
        f"provider_error={outcome.provider_error or 'none'}",
        f"verdict={outcome.report.verdict}",
        f"score={outcome.report.score}",
    ]
    (out_dir / "run.txt").write_text("\n".join(run_lines) + "\n", encoding="utf-8")


def run_proof_audit(
    repo_path: str,
    *,
    provider: str = "openrouter",
    model: str | None = None,
    base_url: str | None = None,
    probe_url: str | None = None,
    out_dir: str | Path | None = None,
    session_id: str | None = None,
    allow_offline_fallback: bool = True,
    timeout_seconds: float = 90.0,
) -> AuditRunOutcome:
    """Execute the 2-stage ProofAudit Minion workflow over a target repository."""
    resolved_repo = str(Path(repo_path).resolve())
    resolved_model = (model or "").strip() or DEFAULT_MODELS.get(provider, "model-id")
    resolved_base_url = (base_url or "").strip() or DEFAULT_ENDPOINTS.get(provider, "")
    resolved_probe_url = (probe_url or "").strip() or resolved_base_url or "https://openrouter.ai/api/v1"
    resolved_session = (session_id or "").strip() or f"proof-audit-{uuid4().hex[:10]}"

    approvals: list[dict[str, Any]] = []

    def _approval_callback(tool_name: str, args: dict[str, Any], approval_id: str) -> bool:
        approvals.append(
            {
                "tool_name": tool_name,
                "args": args,
                "approval_id": approval_id,
                "approved": True,
            }
        )
        return True

    facts: dict[str, Any] = {}
    used_offline_fallback = False
    provider_error_msg: str | None = None
    report: ProofAuditReport | None = None

    with tempfile.TemporaryDirectory(prefix="proof-audit-om-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        config_path = build_isolated_runtime_config(
            work_dir=tmp_path,
            provider=provider,
            model=resolved_model,
            base_url=resolved_base_url,
        )
        runtime = APIRuntime.from_config_path(
            str(config_path),
            home_root=tmp_path,
            data_root=tmp_path,
        )
        try:
            collector_prompt = (
                f"Audit the repository at '{resolved_repo}' and probe endpoint '{resolved_probe_url}'. "
                "Call inspect_repo_manifest, scan_sdk_surface, probe_openai_compatible_endpoint, "
                "and run_repo_smoke_check, then summarize all collected JSON facts."
            )
            with Agent(
                runtime=runtime,
                agent_id="default",
                instructions=(
                    "You are ProofAudit Collector. Run all 4 audit tools on the target repository "
                    "and endpoint, then return a concise summary of the tool outputs."
                ),
                tools=[
                    inspect_repo_manifest,
                    scan_sdk_surface,
                    probe_openai_compatible_endpoint,
                    run_repo_smoke_check,
                ],
                session_id=resolved_session,
            ) as collector:
                collector_result = collector.run(
                    collector_prompt,
                    session_id=resolved_session,
                    timeout_seconds=timeout_seconds,
                    approval_callback=_approval_callback,
                )

            facts = collect_deterministic_facts(resolved_repo, resolved_probe_url)
            facts["collector_text"] = collector_result.text

            judge_prompt = (
                "Produce a ProofAuditReport JSON object from these verified repository audit facts:\n"
                f"{json.dumps(facts, indent=2)}"
            )
            with Agent(
                runtime=runtime,
                agent_id="default",
                instructions=(
                    "You are ProofAudit Verdict Judge. Return valid JSON matching ProofAuditReport "
                    "with fields: repo_name, verdict (READY|WARNINGS|BLOCKED), score (0-100), "
                    "building_blocks_detected, findings, remediation_steps, summary."
                ),
                output_type=ProofAuditReport,
                session_id=resolved_session,
            ) as judge:
                judge_result = judge.run(
                    judge_prompt,
                    session_id=resolved_session,
                    timeout_seconds=timeout_seconds,
                )
                report = judge_result.output
        except (ProviderError, AgentOutputValidationError, TurnTimeoutError) as exc:
            provider_error_msg = f"{type(exc).__name__}: {exc}"
            if not allow_offline_fallback:
                raise
            used_offline_fallback = True
            if not facts:
                facts = collect_deterministic_facts(resolved_repo, resolved_probe_url)
            report = build_offline_report(
                resolved_repo,
                facts,
                note=f"deterministic fallback after {type(exc).__name__}",
            )
        finally:
            runtime.close()

    assert report is not None
    out_path = Path(out_dir).resolve() if out_dir else None
    outcome = AuditRunOutcome(
        report=report,
        facts=facts,
        session_id=resolved_session,
        approvals=approvals,
        used_offline_fallback=used_offline_fallback,
        provider_error=provider_error_msg,
        out_dir=out_path,
    )

    if out_path is not None:
        write_audit_artifacts(
            out_dir=out_path,
            outcome=outcome,
            provider=provider,
            model=resolved_model,
            base_url=resolved_base_url,
        )

    return outcome
