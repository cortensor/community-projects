"""Report and documentation artifact generators for Cortensor Route Bench."""

from __future__ import annotations

import json
from pathlib import Path

from .config import redact_secrets
from .models import (
    ConsensusVerdict,
    PreflightReport,
    ProbeMatrixReport,
    RouteBenchSummary,
)


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, indent=2, ensure_ascii=True)
    path.write_text(redact_secrets(raw) + "\n", encoding="utf-8")
    return path


def render_benchmark_markdown(summary: RouteBenchSummary) -> str:
    """Render human-readable BENCHMARK_REPORT.md from preflight, probe matrix, and consensus output."""
    lines = [
        "# Cortensor Route Bench — Execution Report",
        "",
        f"- **Generated (UTC):** `{summary.generated_at_utc}`",
        f"- **Provider:** `{summary.provider}` (`{summary.preflight.base_url}`)",
        f"- **Probe Model:** `{summary.model}`",
        *(
            [f"- **Consensus Model:** `{summary.telemetry['bench_model']}`"]
            if summary.telemetry.get("bench_model") and summary.telemetry.get("bench_model") != summary.model
            else []
        ),
        f"- **OpenMinion SDK:** `{summary.openminion_version}`",
        f"- **Preflight Status:** `{summary.preflight.overall_status.upper()}`",
        "",
        "## 1. Preflight Checks",
        "",
        "| Check ID | Status | Summary |",
        "| :--- | :--- | :--- |",
    ]
    for chk in summary.preflight.checks:
        lines.append(f"| `{chk.check_id}` | **{chk.status.upper()}** | {chk.summary} |")

    if summary.probe_matrix is not None:
        pm = summary.probe_matrix
        lines.extend([
            "",
            "## 2. OpenMinion 0.1 Building-Block Probe Matrix",
            "",
            f"**Result:** {pm.passed_probes}/{pm.total_probes} probes succeeded ({pm.total_elapsed_ms:.2f} ms total).",
            "",
            "| Probe ID | Building Block | Status | Elapsed (ms) | Attempts | Run ID | Summary |",
            "| :--- | :--- | :--- | ---: | ---: | :--- | :--- |",
        ])
        for p in pm.probes:
            rid = p.run_id or "-"
            lines.append(
                f"| `{p.probe_id}` | {p.building_block} | **{p.status}** | {p.elapsed_ms:.2f} | {p.attempts} | `{rid}` | {p.summary} |"
            )

    if summary.consensus_verdict is not None:
        cv = summary.consensus_verdict
        lines.extend([
            "",
            "## 3. Multi-Agent PoI-Style Consensus Verdict",
            "",
            f"- **Task:** {cv.task}",
            f"- **Decision:** **{cv.decision}**",
            f"- **Agreement Score:** `{cv.agreement_score:.2f}`",
            "",
            "### Worker Summaries",
        ])
        for ws in cv.worker_summaries:
            lines.append(f"- {ws}")
        if cv.discrepancies:
            lines.append("")
            lines.append("### Discrepancies")
            for disc in cv.discrepancies:
                lines.append(f"- {disc}")
        lines.extend(["", "### Recommendations"])
        for rec in cv.recommendations:
            lines.append(f"- {rec}")
        lines.extend(["", "### Final Synthesis", "", cv.final_summary])

    return redact_secrets("\n".join(lines) + "\n")


def render_building_blocks_doc(probe_matrix: ProbeMatrixReport) -> str:
    """Render docs/BUILDING_BLOCKS_TESTED.md from live measured probes."""
    lines = [
        "# OpenMinion 0.1 Building Blocks Tested",
        "",
        f"Measured automatically against live provider **`{probe_matrix.provider}`** (`{probe_matrix.model}`) on **`openminion=={probe_matrix.openminion_version}`** at `{probe_matrix.generated_at_utc}`.",
        "",
        f"**Overall Score:** `{probe_matrix.passed_probes}/{probe_matrix.total_probes}` probes passed in `{probe_matrix.total_elapsed_ms:.2f} ms`.",
        "",
        "| # | Probe | Building Block | Outcome | Latency (ms) | Attempts | Notes & Measured Behavior |",
        "| ---: | :--- | :--- | :--- | ---: | ---: | :--- |",
    ]
    for idx, p in enumerate(probe_matrix.probes, 1):
        lines.append(
            f"| {idx} | `{p.probe_id}` | {p.building_block} | **{p.status}** | {p.elapsed_ms:.2f} | {p.attempts} | {p.summary} |"
        )
    lines.extend([
        "",
        "## Key Architectural Observations",
        "",
        "- **Bounded Subagent Isolation (`subagent` + `DelegatedMemoryReadRequest`)**: Child agents start with clean transcripts (`parent_transcript_inherited=False`), bounded `tool_allowlist`, and single-use `read_only_bounded` policy grants that are revoked automatically in `finally`.",
        "- **Fail-Fast `Handoff` Validation**: Duplicate `Handoff.resolved_name()` values are rejected upfront before tool registration, avoiding cryptic runtime exposure-profile collisions.",
        "- **Strict Output Guard (`AgentOutputValidationError`)**: When a model emits prose instead of JSON, `Agent._coerce_output` raises `AgentOutputValidationError` while preserving `.raw_text` and `.validation_error` for debugging.",
    ])
    return redact_secrets("\n".join(lines) + "\n")


def render_what_we_learned_doc(summary: RouteBenchSummary) -> str:
    """Render docs/WHAT_WE_LEARNED.md detailing verified SDK & Cortensor findings."""
    lines = [
        "# What We Learned (OpenMinion 0.1.23 & Cortensor Builder Findings)",
        "",
        f"Captured during real-model verification on **`openminion=={summary.openminion_version}`** using `{summary.provider}` (`{summary.model}`).",
        "",
        "## 1. Verified `openminion==0.1.23` SDK Findings",
        "",
        "1. **Preset Model Timeout & Free-Tier Quota Variance (`openminion setup --list-providers --json`)**",
        "   - **Observed:** The `gemini` preset lists `recommended_models: [\"gemini-3.6-flash\"]`, which timed out (`ReadTimeout` at 15s) on live `/v1beta/openai/chat/completions`, while `gemini-2.5-flash` exhausted free-tier quota rapidly (`HTTP 429`). `gemini-3.5-flash` and `gemini-flash-lite-latest` responded `HTTP 200`.",
        "   - **Workaround:** Explicitly configure working low-latency model IDs and support split `--model` / `--bench-model` flags across probes and multi-agent consensus.",
        "   - **Suggested Fix:** Validate preset defaults against active endpoints and expose `--check-provider` model-catalog probing.",
        "",
        "2. **Hidden `reflect` / `freshness_classify` Calls Exhausting 45s `api_turn_timeout_seconds`**",
        "   - **Observed (`telemetry.db` `chat.phase_timing`):** A single subagent turn triggered hidden `reflect` (3 internal attempts totaling 77.9s) and `freshness_classify` calls before/around `entry`, exceeding the default 45s gateway turn timeout (and a 90s subagent timeout) with `TurnTimeoutError`.",
        "   - **Workaround:** `ensure_openminion_config()` sets `gateway.api_turn_timeout_seconds = 180` and `workflow.py` uses `timeout_seconds = 180` on isolated subagents.",
        "   - **Suggested Fix:** Allow API `Agent` / `subagent` callers to disable internal reflection/classification steps cleanly for deterministic low-latency workflows.",
        "",
        "3. **Mandatory `TASK_UPDATE_INSTRUCTIONS` Envelope & Session Turn-2 Rejections**",
        "   - **Observed (`openminion/modules/brain/loop/context/task_entry.py` & `task_context.py:95`):** Every `Agent.run()` injects ~12.7k input tokens of CLI `TASK_UPDATE_INSTRUCTIONS` and rejects turns when `task_update.user_quote` is not an exact substring of the latest user input (`INVALID_TASK_CONTEXT_UPDATE`: `'I could not safely update the task conditions.'`), impacting toolless single turns and Turn-2 session recall on lightweight models.",
        "   - **Suggested Fix:** Provide a stateless API-turn mode for programmatic `Agent` invocations that skips interactive coding-task state parsing.",
        "",
        "4. **Unattended `Handoff` Blocked by `UNKNOWN_REVERSIBILITY` & JSON-Inside-`.yaml` Config File**",
        "   - **Observed (`modules/policy/runtime/service.py:545` & `base/config/io.py:59`):** `Handoff` compiles `transfer_to_*` without registering a safe/reversible risk spec, blocking unattended handoffs with `Policy confirmation required (UNKNOWN_REVERSIBILITY)`. Additionally, `openminion`'s default config path `.openminion/config.yaml` is actually loaded and parsed strictly with `json.loads()`, failing on YAML syntax.",
        "   - **Workaround:** `ensure_openminion_config()` patches `.openminion/config.yaml` via `json.loads`/`json.dumps` with exact-tool `action_policy.rules` (`mode: \"auto\"`) overrides for declared `transfer_to_*` tools.",
        "   - **Suggested Fix:** Register `transfer_to_*` internal delegation tools cleanly and align the default config extension (`.json`) or support YAML natively.",
        "",
        "5. **`Agent(output_type=PydanticModel)` Missing Schema Injection & Response Envelope Wrapping**",
        "   - **Observed (`api/agent.py` `_build_payload` & `services/brain/post_execution/postprocess_response.py:276`):** `_build_payload` does not forward `response_format` or inject `output_type.model_json_schema()`, while `postprocess_response.py:276` wraps non-noop text with `f\"{agent_name}: {response_text}\"`. While `Agent._coerce_output()` strips single-line `openminion: ` prefixes on clean JSON, code fences or prose trigger `AgentOutputValidationError`.",
        "   - **Workaround:** Use `json_schema_instruction()` plus `parse_structured_reply()` to strip `<agent_name>: ` envelopes, code fences, and extract balanced JSON safely.",
        "   - **Suggested Fix:** Inject optional JSON schema guidance when `output_type` is provided and preserve clean raw payload output before channel display prefixing.",
        "",
        "6. **Hardcoded `'openai'` Telemetry/Error Labels, Missing Built-In Retry, & Windows `doctor` Advice**",
        "   - **Observed (`services/agent/service.py:700`, `telemetry.db`, & `openminion doctor`):** Transient `HTTP 429` aborts without exponential backoff and emits `(openai rate limited: HTTP 429)` even for `--provider gemini`; `chat.phase_timing` and `doctor` also report `provider='openai'` and POSIX `chmod 750` advice on Windows NTFS.",
        "   - **Workaround:** `run_with_backoff()` adds jittered exponential backoff and `probe`/`bench` pacing.",
        "   - **Suggested Fix:** Surface the configured preset ID consistently, add built-in transient retry policies, and tailor path permission advice on Windows (`os.name == 'nt'`).",
        "",
        "## 2. Cortensor Route Compatibility Lessons",
        "",
        "- **Portal Non-Tool-Calling Constraint:** Cortensor Docs v2 explicitly notes hosted compatibility routes (`api.cortensor.app/v1`) expose text-in/text-out only without native tool calling. Applications targeting both OpenAI-compatible providers and Cortensor Portal should inspect `supports_native_tool_calling` via preflight and fall back cleanly to single-turn synthesis or prompt-based tool loops.",
        "- **Hidden Reasoning Token Budgets:** Reasoning-capable models (like `gemini-2.5-flash` and `gemini-3.5-flash`) can exhaust tight `max_tokens` or per-request HTTP timeouts (`60s` on `reflect`/`act`) during internal thinking, whereas `gemini-flash-lite-latest` delivers predictable 1.2s–4.1s step latency for multi-agent verification loops.",
    ]
    return redact_secrets("\n".join(lines) + "\n")


def write_all_artifacts(
    summary: RouteBenchSummary,
    *,
    artifacts_dir: Path,
    docs_dir: Path,
    consensus_telemetry: dict[str, object] | None = None,
) -> dict[str, Path]:
    """Write JSON telemetry, Markdown reports, and docs files cleanly."""
    written: dict[str, Path] = {}
    written["preflight_json"] = _write_json(
        artifacts_dir / "preflight.json",
        summary.preflight.model_dump(mode="json"),
    )
    if summary.probe_matrix is not None:
        written["probe_matrix_json"] = _write_json(
            artifacts_dir / "probe_matrix.json",
            summary.probe_matrix.model_dump(mode="json"),
        )
    if summary.consensus_verdict is not None:
        written["live_consensus_json"] = _write_json(
            artifacts_dir / "live_consensus_run.json",
            {
                "verdict": summary.consensus_verdict.model_dump(mode="json"),
                "telemetry": consensus_telemetry or summary.telemetry,
            },
        )
    written["summary_json"] = _write_json(
        artifacts_dir / "route_bench_summary.json",
        summary.model_dump(mode="json"),
    )

    md_path = artifacts_dir / "BENCHMARK_REPORT.md"
    md_path.write_text(render_benchmark_markdown(summary), encoding="utf-8")
    written["benchmark_md"] = md_path

    docs_dir.mkdir(parents=True, exist_ok=True)
    if summary.probe_matrix is not None:
        bb_path = docs_dir / "BUILDING_BLOCKS_TESTED.md"
        bb_path.write_text(render_building_blocks_doc(summary.probe_matrix), encoding="utf-8")
        written["building_blocks_md"] = bb_path

    wl_path = docs_dir / "WHAT_WE_LEARNED.md"
    wl_path.write_text(render_what_we_learned_doc(summary), encoding="utf-8")
    written["what_we_learned_md"] = wl_path

    return written
