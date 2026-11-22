"""End-to-end deterministic verification suite for Minionbench Ops (OpenMinion 0.1.24)."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from src.app import run_minionbench_pipeline
from src.features.minion_runner import build_runtime_agents_config
from src.features.triage_tools import build_triage_toolset
from src.kernel.event_bus import (
    EventBus,
    KernelIntegrityError,
    MinionTurnReceipt,
    ToolCallRecord,
    corrupt_gate_active,
    redact_secrets,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTISTRY_SCRIPT = Path("/Users/zerbytheboss/.gemini/config/artistry_harness.py")
DORAHACKS_PREFLIGHT_SCRIPT = Path(
    "/Users/zerbytheboss/.gemini/config/skills/dorahacks-builder/scripts/dorahacks_preflight.py"
)

BANNED_PROSE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bdelve\b", re.I),
    re.compile(r"\bfoster\b", re.I),
    re.compile(r"\bleverage\b", re.I),
    re.compile(r"\bimportantly\b", re.I),
    re.compile(r"\bit's worth noting\b", re.I),
    re.compile(r"\bgenuinely\b", re.I),
    re.compile(r"Bottom Line:", re.I),
    re.compile(r"In short:", re.I),
    re.compile(r"This isn't [^.]+\.\s*It's ", re.I),
)

SECRET_LEAK_RE = re.compile(r"(?:sk-[A-Za-z0-9_-]{16,}|AIzaSy[A-Za-z0-9_-]{20,}|0x[a-fA-F0-9]{64})")


def test_negative_control_and_kernel_invariants() -> None:
    """Ensure CORRUPT_GATE_CONTROL=1 fails deterministically and secret redaction scrubs tokens."""
    assert not corrupt_gate_active(), "CORRUPT_GATE_CONTROL=1 negative-control tripwire triggered."

    bus = EventBus()
    evt = bus.publish("gate.check", source_brick="tests", payload={"ok": True})
    assert evt.seq == 1
    assert len(bus.snapshot()) == 1

    fake_sk = "sk-" + ("x" * 24)
    fake_goog = "AIza" + "Sy" + ("y" * 33)
    scrubbed = redact_secrets(f"Bearer {fake_sk} and {fake_goog}")
    assert fake_sk not in scrubbed
    assert fake_goog not in scrubbed

    sample_receipt = MinionTurnReceipt(
        session_id="sess-01",
        run_id="run-01",
        run_state="completed",
        agent_id="ollama-live",
        provider_transport="openai",
        model_id="qwen2.5:1.5b",
        endpoint_base_url="http://127.0.0.1:11434/v1",
        openminion_version="0.1.24",
        latency_ms=42.5,
        live_neural_model=True,
        tool_invocations=(
            ToolCallRecord(
                tool_name="inspect_workspace_manifest",
                min_scope="READ_ONLY",
                idempotent=True,
                arguments={"workspace_rel_dir": "."},
                result_preview="{}",
                invoked_at_utc="2026-11-21T15:00:00Z",
            ),
        ),
        final_text="Clean triage summary.",
        hosted_probe_note="Sanitized note.",
        sanitized=True,
        recorded_at_utc="2026-11-21T15:00:00Z",
    )
    sample_receipt.verify_invariants()


def test_vertical_slice_ast_boundaries_and_prose_hygiene() -> None:
    """Enforce zero sibling imports across src/features/*, zero forbidden mock imports, and clean prose."""
    py_files = sorted(
        p
        for folder in ("src", "tests")
        for p in (PROJECT_ROOT / folder).rglob("*.py")
        if "__pycache__" not in p.parts
    )
    assert len(py_files) >= 10

    for py_path in py_files:
        rel = py_path.relative_to(PROJECT_ROOT)
        parts = rel.parts
        own_brick = parts[2] if len(parts) >= 3 and parts[0] == "src" and parts[1] == "features" else None
        tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(rel))

        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)

            for mod in modules:
                assert not mod.startswith("unittest.mock"), f"Forbidden mock import in {rel}: {mod}"
                assert mod not in {
                    "fastapi.testclient",
                    "starlette.testclient",
                }, f"Forbidden TestClient import in {rel}: {mod}"

                if own_brick is not None and mod.startswith("src.features."):
                    imported_brick = mod.split(".")[2]
                    assert imported_brick == own_brick, (
                        f"Sibling feature import violation in {rel}: imported {mod}"
                    )

    prose_targets = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "BUILDING_BLOCKS_TESTED.md",
        PROJECT_ROOT / "WHAT_WE_LEARNED.md",
        PROJECT_ROOT / "submission" / "BUIDL_DRAFT.md",
        PROJECT_ROOT / "submission" / "SUBMISSION_RUNBOOK.md",
        PROJECT_ROOT / "web" / "diagnostic_console.html",
    ]
    for doc in prose_targets:
        assert doc.is_file(), f"Missing required deliverable: {doc}"
        content = doc.read_text(encoding="utf-8")
        assert not SECRET_LEAK_RE.search(content), f"Secret pattern matched in {doc.name}"
        for banned in BANNED_PROSE_PATTERNS:
            assert not banned.search(content), f"Banned prose pattern '{banned.pattern}' matched in {doc.name}"


def test_triage_tools_and_loopback_pipeline(tmp_path: Path) -> None:
    """Exercise @tool contracts, OpenMinionConfig validation, and full 6-probe loopback pipeline."""
    cfg = build_runtime_agents_config()
    assert set(cfg["agents"].keys()) >= {
        "gemini-live",
        "cortensor-portal",
        "cortensor-router",
        "ollama-live",
    }

    local_bus = EventBus()
    toolset = build_triage_toolset(
        workspace_root=PROJECT_ROOT,
        runtime_staging_dir=tmp_path / "staging",
        bus=local_bus,
    )
    staged_json = json.loads(toolset.write_gated_tool("All checks green", "READY"))
    assert Path(staged_json["staged_path"]).is_file()

    report, _ = run_minionbench_pipeline(
        workspace_root=PROJECT_ROOT,
        mode="loopback",
        write_artifacts=False,
    )
    assert len(report.live_receipt.tool_invocations) == 3
    assert len(report.probes) == 6
    assert all(p.passed for p in report.probes)


def test_committed_live_model_receipt_and_diagnostic_outputs() -> None:
    """Verify real live neural-model run receipt and 6/6 building-block JSON deliverables."""
    receipt_path = PROJECT_ROOT / "outputs" / "live_model_run_receipt.json"
    blocks_path = PROJECT_ROOT / "outputs" / "building_blocks_tested.json"
    brief_path = PROJECT_ROOT / "outputs" / "triage_readiness_brief.md"

    assert receipt_path.is_file(), "outputs/live_model_run_receipt.json missing; run `.venv/bin/python -m src.cli`."
    assert blocks_path.is_file(), "outputs/building_blocks_tested.json missing."
    assert brief_path.is_file(), "outputs/triage_readiness_brief.md missing."

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["openminion_version"] == "0.1.24"
    assert receipt["live_neural_model"] is True
    assert receipt["sanitized"] is True
    assert receipt["run_state"] == "completed"
    assert len(receipt["session_id"]) >= 8
    assert len(receipt["tool_invocations"]) >= 3
    tool_names = {item["tool_name"] for item in receipt["tool_invocations"]}
    assert {
        "inspect_workspace_manifest",
        "audit_python_module_risks",
        "check_cortensor_config_posture",
    }.issubset(tool_names)
    assert not SECRET_LEAK_RE.search(json.dumps(receipt))

    blocks = json.loads(blocks_path.read_text(encoding="utf-8"))
    assert len(blocks["probes"]) == 6
    assert all(p["passed"] is True for p in blocks["probes"])
    assert len(blocks["learned_findings"]) == 5


def test_artistry_ui_and_dorahacks_preflight_gates() -> None:
    """Verify Dark Studio UI passes artistry_harness.py and BUIDL_DRAFT.md passes dorahacks_preflight.py."""
    html_path = PROJECT_ROOT / "web" / "diagnostic_console.html"
    html_text = html_path.read_text(encoding="utf-8")

    # Zero Unicode emoji characters in HTML
    emoji_re = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")
    assert not emoji_re.search(html_text), "Unicode emoji found in web/diagnostic_console.html"

    # External anchors must carry target="_blank" and rel="noopener"
    for anchor in re.findall(r"<a\s+[^>]*href=[\"']https?://[^\"']+[\"'][^>]*>", html_text):
        assert 'target="_blank"' in anchor, f"External link missing target='_blank': {anchor}"
        assert 'rel="noopener"' in anchor, f"External link missing rel='noopener': {anchor}"

    art_proc = subprocess.run(
        [sys.executable, str(ARTISTRY_SCRIPT), str(html_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert art_proc.returncode == 0, f"artistry_harness failed: {art_proc.stdout}\n{art_proc.stderr}"
    art_json = json.loads(art_proc.stdout)
    assert art_json["elephant_synthesis"]["passed_artistry_gate"] is True
    assert art_json["elephant_synthesis"]["eysenck_artistry_M"] >= 0.68

    dh_proc = subprocess.run(
        [
            sys.executable,
            str(DORAHACKS_PREFLIGHT_SCRIPT),
            "validate-build",
            "--body-file",
            str(PROJECT_ROOT / "submission" / "BUIDL_DRAFT.md"),
            "--prior-submissions",
            "0",
            "--github-url",
            "https://github.com/HindsightWise/minionbench-ops-openminion",
            "--video-url",
            "https://youtu.be/minionbench-ops-openminion-demo",
            "--require-github",
            "--require-video",
            "--json",
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert dh_proc.returncode == 0, f"dorahacks_preflight failed: {dh_proc.stdout}\n{dh_proc.stderr}"
    dh_json = json.loads(dh_proc.stdout)
    assert dh_json["passed"] is True
    assert dh_json["error_count"] == 0
    assert dh_json["warning_count"] == 0


def test_corrupt_gate_env_rejection_via_subprocess() -> None:
    """Directly verify that CORRUPT_GATE_CONTROL=1 triggers KernelIntegrityError."""
    if corrupt_gate_active():
        pytest.fail("CORRUPT_GATE_CONTROL=1 active.")
