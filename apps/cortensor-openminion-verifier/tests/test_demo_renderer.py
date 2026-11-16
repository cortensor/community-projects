"""Behavioral tests for captioned 1080p MP4 demo rendering and render-demo CLI."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import imageio.v2 as imageio
import numpy as np
import pytest

from cortensor_verifier.cli import main
from cortensor_verifier.demo_renderer import (
    DEFAULT_DEMO_DURATION_SECONDS,
    DEMO_HEIGHT,
    DEMO_WIDTH,
    TOTAL_SCENES,
    _SCENE_CAPTIONS,
    _SCENE_TITLES,
    _build_scene_terminal_lines,
    _load_font,
    load_demo_inputs,
    render_demo_video,
)
from cortensor_verifier.probe import EXPECTED_PROBE_IDS


def _sample_payload() -> dict[str, Any]:
    return {
        "calibration_meta": {
            "sdk_version": "0.1.21",
            "preset": "openai-compatible",
            "model": "grok-4.6",
            "base_url_host": "https://<configured-openai-compatible-relay>/v1",
            "calibration_status": "[Live LLM Calibrated]",
            "generated_at": "2026-11-14T15:30:00+00:00",
        },
        "audit_bundle": {
            "claim_id": "delphi-btc-etf-2024",
            "preset": "openai-compatible",
            "dossier": {
                "claim_id": "delphi-btc-etf-2024",
                "title": "US Spot Bitcoin ETP Approval (January 2024)",
                "claim": (
                    "The U.S. SEC approved the listing and trading of multiple spot Bitcoin "
                    "exchange-traded products on January 10, 2024."
                ),
                "market_question": "Did the U.S. SEC approve spot Bitcoin ETPs on January 10, 2024?",
                "resolution_criteria": (
                    "Resolve SUPPORTED only if official SEC approval orders or Chair statement "
                    "confirm approval dated 2024-01-10."
                ),
                "source_hints": ["sec-spot-btc-2024-01-10", "federal-register-34-99306"],
                "tags": ["delphi", "regulation"],
                "metadata": {"market_id": "delphi-mkt-2024-001"},
            },
            "consensus": {
                "claim_id": "delphi-btc-etf-2024",
                "final_verdict": "SUPPORTED",
                "agreement_score": 0.99,
                "mean_confidence": 0.96,
                "disagreement_summary": "Corroborator and skeptic agreed on SUPPORTED.",
                "requires_human_review": False,
                "passes": [
                    {
                        "verdict": "SUPPORTED",
                        "confidence": 0.97,
                        "rationale": "SEC order 34-99306 and Chair statement confirm 2024-01-10 approval.",
                        "pass_role": "corroborator",
                        "citations": [
                            {
                                "source_id": "sec-spot-btc-2024-01-10",
                                "title": "Statement on the Approval of Spot Bitcoin Exchange-Traded Products",
                                "excerpt": "approved the listing and trading on January 10, 2024",
                            }
                        ],
                    },
                    {
                        "verdict": "SUPPORTED",
                        "confidence": 0.95,
                        "rationale": "Checked official filings; no contradictory SEC rescission found.",
                        "pass_role": "skeptic",
                        "citations": [
                            {
                                "source_id": "federal-register-34-99306",
                                "title": "SEC Release No. 34-99306 Order",
                                "excerpt": "Order Granting Accelerated Approval dated January 10, 2024",
                            }
                        ],
                    },
                ],
            },
            "tool_calls": ["load_delphi_market_fixture", "search_public_evidence", "fetch_source_excerpt"],
            "session_id": "cal-btc-etf-01",
            "publication": {
                "requested": True,
                "published": True,
                "publication_status": "published",
                "claim_id": "delphi-btc-etf-2024",
                "final_verdict": "SUPPORTED",
                "approval_mode": "allow_once",
                "thread_id": "thread-cal-pub-01",
                "approval_id": "appr-cal-01",
                "log_path": ".openminion-state/published_verdicts.jsonl",
            },
            "metadata": {
                "telemetry": {
                    "requests": 7,
                    "prompt_tokens": 1820,
                    "completion_tokens": 410,
                    "total_tokens": 2230,
                    "total_latency_ms": 42100,
                }
            },
        },
        "probe_report": {
            "suite_name": "openminion-0.1-building-blocks",
            "sdk_version": "0.1.21",
            "preset": "openai-compatible",
            "model": "grok-4.6",
            "base_url_host": "https://<configured-openai-compatible-relay>/v1",
            "calibration_status": "[Live LLM Calibrated]",
            "generated_at": "2026-11-14T15:30:00+00:00",
            "total_probes": len(EXPECTED_PROBE_IDS),
            "passed_probes": len(EXPECTED_PROBE_IDS),
            "failed_probes": 0,
            "total_latency_ms": 185000.0,
            "probes": [
                {
                    "probe_id": pid,
                    "name": f"Block {idx}: {pid}",
                    "passed": True,
                    "detail": f"Verified {pid} against real openminion runtime.",
                    "latency_ms": 1200.0 + idx * 100.0,
                    "metadata": {},
                }
                for idx, pid in enumerate(EXPECTED_PROBE_IDS, start=1)
            ],
            "dx_findings": [
                {
                    "title": "Explicit thread_id Required for Session Continuity",
                    "observation": "Must forward both session_id and thread_id across Agent.run turns.",
                },
                {
                    "title": "90s Turn-Timeout Default & Handoff Paraphrasing",
                    "observation": "Forward explicit timeout_seconds to Agent.run and subagent.",
                },
            ],
        },
    }


def test_default_duration_bounds_and_validation() -> None:
    assert 60 <= DEFAULT_DEMO_DURATION_SECONDS <= 300
    assert (DEMO_WIDTH, DEMO_HEIGHT) == (1920, 1080)

    sample = _sample_payload()
    with pytest.raises(ValueError, match="between 60 and 300"):
        render_demo_video(
            output_path=Path("unused-too-short.mp4"),
            audit_bundle=sample["audit_bundle"],
            probe_report=sample["probe_report"],
            duration_seconds=15,
            fps=4,
        )

    with pytest.raises(ValueError, match="between 60 and 300"):
        render_demo_video(
            output_path=Path("unused-too-long.mp4"),
            audit_bundle=sample["audit_bundle"],
            probe_report=sample["probe_report"],
            duration_seconds=360,
            fps=4,
        )


def test_render_demo_video_outputs_1080p_mp4_with_scene_progression(tmp_path: Path) -> None:
    sample = _sample_payload()
    out_mp4 = tmp_path / "cortensor_demo.mp4"

    result = render_demo_video(
        output_path=out_mp4,
        audit_bundle=sample["audit_bundle"],
        probe_report=sample["probe_report"],
        duration_seconds=60,
        fps=1,
    )

    assert out_mp4.exists()
    assert out_mp4.stat().st_size > 10_000
    assert result.width == 1920
    assert result.height == 1080
    assert result.duration_seconds == pytest.approx(60.0)
    assert result.scene_count == 7

    reader = imageio.get_reader(out_mp4, format="ffmpeg")
    try:
        frames = [frame for frame in reader]
    finally:
        reader.close()

    assert len(frames) == 60
    first = frames[0]
    last = frames[-1]
    assert first.shape == (1080, 1920, 3)
    assert last.shape == (1080, 1920, 3)
    assert float(first.std()) > 10.0
    assert float(last.std()) > 10.0
    assert not (first == last).all()


def test_render_demo_video_fails_closed_on_plaintext_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_token = "sk-demo-forbidden-leak-99887766"
    monkeypatch.setenv("OPENAI_API_KEY", secret_token)
    sample = _sample_payload()
    sample["audit_bundle"]["consensus"]["disagreement_summary"] = (
        f"Accidental secret bearer {secret_token} should block video rendering."
    )

    with pytest.raises(ValueError, match="unredacted"):
        render_demo_video(
            output_path=tmp_path / "blocked.mp4",
            audit_bundle=sample["audit_bundle"],
            probe_report=sample["probe_report"],
            duration_seconds=60,
            fps=1,
            secret_env_names=["OPENAI_API_KEY"],
        )


def test_cli_render_demo_works_across_external_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_mp4 = tmp_path / "cli_demo.mp4"
    external_dir = tmp_path / "elsewhere"
    external_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(external_dir)

    rc = main(
        [
            "render-demo",
            "-o",
            str(out_mp4),
            "--duration-seconds",
            "60",
            "--fps",
            "1",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["width"] == 1920
    assert payload["height"] == 1080
    assert payload["scene_count"] == 7
    assert out_mp4.exists() and out_mp4.stat().st_size > 10_000


def test_demo_renderer_wraps_all_scene_captions_within_card_bounds(tmp_path: Path) -> None:
    sample = _sample_payload()
    out_mp4 = tmp_path / "caption_bounds_check.mp4"
    result = render_demo_video(
        output_path=out_mp4,
        audit_bundle=sample["audit_bundle"],
        probe_report=sample["probe_report"],
        duration_seconds=70,
        fps=1,
    )
    assert result.frame_count == 70
    assert result.scene_count == TOTAL_SCENES

    reader = imageio.get_reader(out_mp4, format="ffmpeg")
    try:
        frames = [frame for frame in reader]
    finally:
        reader.close()
    assert len(frames) == 70

    # Sample one late-stage frame from each of the 7 scenes (weights 0.10..0.15 across 70 frames):
    # [0..6], [7..15], [16..26], [27..36], [37..46], [47..59], [60..69]
    scene_probe_frames = [5, 14, 24, 34, 44, 57, 68]
    for scene_idx, frame_idx in enumerate(scene_probe_frames):
        arr = frames[frame_idx]

        # Caption card box is (56, 916, DEMO_WIDTH - 56, 996); text must stay inside x in [76, 1840]
        # and y in [919, 993]. Bright text (#E2E8F0) has max RGB >> 110 (border #334155 is <= 85).
        right_overflow = arr[920:993, DEMO_WIDTH - 80 + 1 :, :].max(axis=2) > 110
        assert not right_overflow.any(), (
            f"Scene {scene_idx + 1} (frame {frame_idx}) caption overflowed right margin x={DEMO_WIDTH - 80}"
        )

        left_overflow = arr[920:993, 60:76, :].max(axis=2) > 110
        assert not left_overflow.any(), f"Scene {scene_idx + 1} caption overflowed left margin."

        bottom_overflow = arr[997:1008, 56 : DEMO_WIDTH - 56, :].max(axis=2) > 90
        assert not bottom_overflow.any(), f"Scene {scene_idx + 1} caption overflowed below y=996."

        # Also ensure upper visualization cards never bleed into the y=697..709 gap above the console.
        upper_gap_bleed = arr[698:709, 56 : DEMO_WIDTH - 56, :].max(axis=2) > 90
        assert not upper_gap_bleed.any(), f"Scene {scene_idx + 1} upper panel bled past y=696."

        # Verify footer progress timer aligns cleanly within right margin x <= DEMO_WIDTH - 50.
        footer_right = arr[1012:, DEMO_WIDTH - 50 :, :]
        assert footer_right.max() < 60, f"Scene {scene_idx + 1} footer timer overflowed right margin."


def test_demo_renderer_animates_live_terminal_execution_within_scene(tmp_path: Path) -> None:
    sample = _sample_payload()
    out_mp4 = tmp_path / "live_terminal_demo.mp4"

    result = render_demo_video(
        output_path=out_mp4,
        audit_bundle=sample["audit_bundle"],
        probe_report=sample["probe_report"],
        duration_seconds=70,
        fps=2,
    )
    assert result.frame_count == 140

    reader = imageio.get_reader(out_mp4, format="ffmpeg")
    try:
        frames = [frame for frame in reader]
    finally:
        reader.close()
    assert len(frames) == 140

    # Scene frame windows for duration=70, fps=2 (140 frames total):
    # Scene 1 (idx 0): 0..13, Scene 2 (idx 1): 14..31, Scene 3 (idx 2): 32..53, Scene 7 (idx 6): 119..139
    intra_scene_pairs = [
        ("scene_1", 0, 12),
        ("scene_2", 14, 28),
        ("scene_3", 32, 52),
        ("scene_7", 119, 138),
    ]
    for label, early_idx, late_idx in intra_scene_pairs:
        early_canvas = frames[early_idx][:900, :, :].astype(np.int16)
        late_canvas = frames[late_idx][:900, :, :].astype(np.int16)
        canvas_diff = int(np.sum(np.abs(early_canvas - late_canvas).max(axis=2) > 20))
        assert canvas_diff > 1500, (
            f"{label} frames {early_idx} vs {late_idx} lacked intra-scene animation "
            f"(changed_pixels={canvas_diff})"
        )

        early_console = frames[early_idx][710:896, 56 : DEMO_WIDTH - 56, :].astype(np.int16)
        late_console = frames[late_idx][710:896, 56 : DEMO_WIDTH - 56, :].astype(np.int16)
        console_diff = int(np.sum(np.abs(early_console - late_console).max(axis=2) > 20))
        assert console_diff > 500, (
            f"{label} frames {early_idx} vs {late_idx} lacked Live Terminal Storyboard streaming "
            f"(console_changed_pixels={console_diff})"
        )

        # Verify both indices actually belong to the same scene (same caption bar).
        early_cap = frames[early_idx][922:990, 80 : DEMO_WIDTH - 80, :].astype(np.int16)
        late_cap = frames[late_idx][922:990, 80 : DEMO_WIDTH - 80, :].astype(np.int16)
        cap_diff = int(np.sum(np.abs(early_cap - late_cap).max(axis=2) > 30))
        assert cap_diff < 50, f"{label} frames {early_idx} vs {late_idx} crossed a scene boundary!"

        # Verify footer progress timer aligns cleanly within right margin x <= DEMO_WIDTH - 50.
        footer_right = frames[late_idx][1012:, DEMO_WIDTH - 50 :, :]
        assert footer_right.max() < 60, f"{label} footer timer overflowed right margin x={DEMO_WIDTH - 50}."


_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]")


def test_demo_renderer_english_only_no_cjk_and_no_private_footer() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    renderer_src = (repo_root / "src" / "cortensor_verifier" / "demo_renderer.py").read_text(
        encoding="utf-8"
    )
    assert not _CJK_RE.search(renderer_src), "demo_renderer.py must contain zero CJK characters."
    assert "PRIVATE" not in renderer_src, "demo_renderer.py must not retain private repo footer warning."
    assert "MIT Licensed · Zero Plaintext Secrets · Offline & Live Reproducible" in renderer_src

    assert len(_SCENE_TITLES) == TOTAL_SCENES
    assert len(_SCENE_CAPTIONS) == TOTAL_SCENES
    for title, subtitle in _SCENE_TITLES:
        assert not _CJK_RE.search(title)
        assert not _CJK_RE.search(subtitle)
        assert subtitle.startswith("Scene ")
    for caption in _SCENE_CAPTIONS:
        assert not _CJK_RE.search(caption)

    cjk_font_markers = ("msyh", "simhei", "notosanscjk", "notoserifcjk", "wqy", "pingfang", "stheiti")
    for bold, mono in ((False, False), (True, False), (False, True), (True, True)):
        font = _load_font(20, bold=bold, mono=mono)
        font_path = str(getattr(font, "path", "")).lower()
        assert not any(marker in font_path for marker in cjk_font_markers), (
            f"_load_font(bold={bold}, mono={mono}) picked CJK font {font_path!r}"
        )


def test_demo_renderer_per_scene_model_badges_and_scene7_cli_flags() -> None:
    from cortensor_verifier import demo_renderer

    sample_diff = _sample_payload()
    sample_diff["audit_bundle"]["metadata"]["calibrated_model"] = "grok-4.6"
    sample_diff["probe_report"]["model"] = "grok-4.7"

    sample_same = _sample_payload()
    sample_same["audit_bundle"]["metadata"]["calibrated_model"] = "grok-4.7"
    sample_same["probe_report"]["model"] = "grok-4.7"

    fonts = demo_renderer._create_fonts()

    # Scenes 0..4 must render audit_model (grok-4.6), distinct from probe_model (grok-4.7)
    for scene_idx in range(5):
        img_audit_46 = np.asarray(
            demo_renderer._render_scene_canvas(
                scene_idx,
                fonts=fonts,
                audit=sample_diff["audit_bundle"],
                probe=sample_diff["probe_report"],
            )
        )
        img_audit_47 = np.asarray(
            demo_renderer._render_scene_canvas(
                scene_idx,
                fonts=fonts,
                audit=sample_same["audit_bundle"],
                probe=sample_same["probe_report"],
            )
        )
        header_badge_diff = int(
            np.sum(np.abs(img_audit_46[80:130, 1200:1880, :].astype(np.int16) - img_audit_47[80:130, 1200:1880, :].astype(np.int16)).max(axis=2) > 20)
        )
        assert header_badge_diff > 20, (
            f"Scene {scene_idx + 1} header model badge did not reflect calibrated_model='grok-4.6' vs 'grok-4.7'"
        )

    # Scene 5 (Scene 6) uses probe_model (grok-4.7) regardless of audit_model (grok-4.6 vs grok-4.7)
    img_s6_diff = np.asarray(
        demo_renderer._render_scene_canvas(
            5,
            fonts=fonts,
            audit=sample_diff["audit_bundle"],
            probe=sample_diff["probe_report"],
        )
    )
    img_s6_same = np.asarray(
        demo_renderer._render_scene_canvas(
            5,
            fonts=fonts,
            audit=sample_same["audit_bundle"],
            probe=sample_same["probe_report"],
        )
    )
    s6_header_diff = int(
        np.sum(np.abs(img_s6_diff[80:130, 1200:1880, :].astype(np.int16) - img_s6_same[80:130, 1200:1880, :].astype(np.int16)).max(axis=2) > 20)
    )
    assert s6_header_diff == 0, "Scene 6 header model badge must depend only on probe_report.model."

    # Scene 6 (Scene 7) header shows combined 'grok-4.6 / grok-4.7', and CLI command #2 reflects calibrated_model
    img_s7_diff = np.asarray(
        demo_renderer._render_scene_canvas(
            6,
            fonts=fonts,
            audit=sample_diff["audit_bundle"],
            probe=sample_diff["probe_report"],
        )
    )
    img_s7_same = np.asarray(
        demo_renderer._render_scene_canvas(
            6,
            fonts=fonts,
            audit=sample_same["audit_bundle"],
            probe=sample_same["probe_report"],
        )
    )
    s7_header_diff = int(
        np.sum(np.abs(img_s7_diff[80:130, 1200:1880, :].astype(np.int16) - img_s7_same[80:130, 1200:1880, :].astype(np.int16)).max(axis=2) > 20)
    )
    assert s7_header_diff > 50, "Scene 7 header badge must display 'grok-4.6 / grok-4.7' when models differ."

    s7_cmd_diff = int(
        np.sum(np.abs(img_s7_diff[340:540, 1160:1850, :].astype(np.int16) - img_s7_same[340:540, 1160:1850, :].astype(np.int16)).max(axis=2) > 20)
    )
    assert s7_cmd_diff > 20, "Scene 7 right-card audit CLI command #2 must explicitly display --model <audit_model>."

    assert hasattr(demo_renderer, "_scene_model_label")
    for idx in range(5):
        assert demo_renderer._scene_model_label(
            idx, audit=sample_diff["audit_bundle"], probe=sample_diff["probe_report"]
        ) == "grok-4.6"
    assert demo_renderer._scene_model_label(
        5, audit=sample_diff["audit_bundle"], probe=sample_diff["probe_report"]
    ) == "grok-4.7"
    assert demo_renderer._scene_model_label(
        6, audit=sample_diff["audit_bundle"], probe=sample_diff["probe_report"]
    ) == "grok-4.6 / grok-4.7"
    assert demo_renderer._scene_model_label(
        6, audit=sample_same["audit_bundle"], probe=sample_same["probe_report"]
    ) == "grok-4.7"


def test_build_scene_terminal_lines_embeds_authentic_json_and_turnchunk_telemetry() -> None:
    from PIL import Image, ImageDraw
    from cortensor_verifier.demo_renderer import _create_fonts
    from cortensor_verifier.probe import assert_no_plaintext_secrets

    audit, probe = load_demo_inputs()
    fonts = _create_fonts()
    draw = ImageDraw.Draw(Image.new("RGB", (DEMO_WIDTH, DEMO_HEIGHT)))

    per_scene_text: list[str] = []
    for scene_idx in range(TOTAL_SCENES):
        lines = _build_scene_terminal_lines(scene_idx, audit=audit, probe=probe)
        assert len(lines) == 5, f"Scene {scene_idx + 1} terminal must have 5 concise lines."
        joined = "\n".join(line for _, line in lines)
        assert not _CJK_RE.search(joined)
        assert_no_plaintext_secrets(joined)
        for _, raw_line in lines:
            assert draw.textlength(raw_line, font=fonts.mono_sm) <= DEMO_WIDTH - 160, (
                f"Scene {scene_idx + 1} terminal line overflows 1760px: {raw_line!r}"
            )
        per_scene_text.append(joined)

    # Scenes 0..4 target calibrated audit_model (grok-4.6); Scene 5 targets probe_model (grok-4.7)
    for scene_idx in range(5):
        assert "--model grok-4.6" in per_scene_text[scene_idx], (
            f"Scene {scene_idx + 1} CLI command must specify --model grok-4.6"
        )
    assert "--model grok-4.7" in per_scene_text[5]

    all_text = "\n".join(per_scene_text)
    for expected_token in (
        '"claim_id": "delphi-btc-etf-2024"',
        '"final_verdict": "SUPPORTED"',
        '"agreement_score": 0.98',
        '"publication_status": "published"',
        '"passed_probes": 10',
        '"total_tokens": 118193',
        '"requests": 20',
        "TurnChunk",
        "11841",
        "430",
    ):
        assert expected_token in all_text, f"Missing authentic telemetry/JSON key: {expected_token!r}"

    # Per-pass telemetry in Scene 3 (scene_idx=2)
    assert "requests=8" in per_scene_text[2] and "total_tokens=52518" in per_scene_text[2]
    assert "requests=7" in per_scene_text[2] and "total_tokens=45617" in per_scene_text[2]


_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def test_submission_docs_and_readme_links_license_and_metadata() -> None:
    from cortensor_verifier.probe import assert_no_plaintext_secrets

    repo_root = Path(__file__).resolve().parents[1]
    pr_draft_path = repo_root / "docs" / "PR_SUBMISSION_DRAFT.md"
    readme_path = repo_root / "README.md"

    pr_text = pr_draft_path.read_text(encoding="utf-8")
    readme_text = readme_path.read_text(encoding="utf-8")

    assert_no_plaintext_secrets(pr_text)
    assert_no_plaintext_secrets(readme_text)

    # Zero broken relative links or ./ or ../ paths in PR_SUBMISSION_DRAFT.md
    pr_links = _MARKDOWN_LINK_RE.findall(pr_text)
    assert pr_links, "docs/PR_SUBMISSION_DRAFT.md must contain explicit GitHub documentation links."
    for target in pr_links:
        assert not target.startswith("./") and not target.startswith("../"), (
            f"PR_SUBMISSION_DRAFT.md contains relative ./ or ../ link: {target!r}"
        )
        assert target.startswith("https://"), (
            f"PR_SUBMISSION_DRAFT.md links inside submission templates must be explicit full HTTPS URLs, got: {target!r}"
        )
    assert "https://github.com/huadeng408/cortensor-openminion-verifier/blob/main/" in pr_text

    # Every relative link in README.md must avoid ./ or ../ and resolve to an existing file in REPO_ROOT
    for target in _MARKDOWN_LINK_RE.findall(readme_text):
        assert not target.startswith("./") and not target.startswith("../"), (
            f"README.md contains broken relative prefix in link: {target!r}"
        )
        if target.startswith(("http://", "https://", "#")):
            continue
        clean_rel = target.split("#", 1)[0]
        assert (repo_root / clean_rel).exists(), (
            f"README.md link target does not exist in repo root: {target!r}"
        )

    # Shared required references in both README.md and docs/PR_SUBMISSION_DRAFT.md
    for name, text in (("README.md", readme_text), ("docs/PR_SUBMISSION_DRAFT.md", pr_text)):
        for required in (
            "MIT",
            "openminion==0.1.21",
            "PROJECTS.yml",
            "STATUS.md",
            "RELEASE.md",
            "UPSTREAM_OPENMINION_BONUS_DRAFTS.md",
            "cortensor_hackathon5_demo.mp4",
        ):
            assert required in text, f"{name} must reference {required!r}"
        assert "Apache-2.0" not in text, f"{name} must not advertise superseded Apache-2.0 license."

    # README.md specific technical coverage
    for readme_req in (
        "load_delphi_market_fixture",
        "search_public_evidence",
        "fetch_source_excerpt",
        "fetch_public_url_excerpt",
        "--fixtures",
        "evidence_sources",
        "English",
        "render-demo",
    ):
        assert readme_req in readme_text, f"README.md missing required technical detail: {readme_req!r}"

    # PR_SUBMISSION_DRAFT.md dual-channel templates & operator checklist
    for pr_req in (
        "DoraHacks",
        "#2418",
        "cortensor/community-projects",
        "apps/cortensor-openminion-verifier/",
        "dev-huadeng408",
        "openminion/openminion",
        "Discord",
        "Public",
        "grok-4.6",
        "grok-4.7",
    ):
        assert pr_req in pr_text, f"docs/PR_SUBMISSION_DRAFT.md missing required checklist/template item: {pr_req!r}"





