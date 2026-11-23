"""Offline tests: fallback briefs, rendering, SQLite store, CLI."""

import json
from pathlib import Path

from fixbrief.cli import main
from fixbrief.fallback import build_fallback_brief
from fixbrief.models import Language, SourceRef
from fixbrief.render import render_markdown
from fixbrief.sources import load_sample
from fixbrief.store import get_brief, list_briefs, save_brief


def _texts():
    return [
        (
            SourceRef(
                title="Samsung Not Charging",
                locator="samsung-not-charging.md",
                kind="offline-sample",
            ),
            load_sample("samsung-not-charging.md"),
        )
    ]


def test_fallback_brief_validates_and_labels_provenance():
    brief = build_fallback_brief(
        "Samsung Galaxy A54", "not charging", _texts(), Language.EN
    )
    assert brief.generated_by == "deterministic-fallback"
    assert brief.device == "Samsung Galaxy A54"
    assert len(brief.likely_causes) >= 2
    assert len(brief.diagnostic_steps) >= 2
    assert len(brief.tools_needed) >= 2
    assert brief.sources[0].locator == "samsung-not-charging.md"
    # Round-trip through JSON must validate identically.
    assert brief.model_dump_json()
    json.loads(brief.model_dump_json())


def test_fallback_brief_spanish_headers_and_tools():
    brief = build_fallback_brief(
        "Samsung Galaxy A54", "not charging", _texts(), Language.ES
    )
    assert brief.language == Language.ES
    markdown = render_markdown(brief)
    assert "Informe de reparación" in markdown
    assert "Causas probables" in markdown


def test_render_markdown_english():
    brief = build_fallback_brief(
        "iPhone 12", "black screen", _texts(), Language.EN
    )
    markdown = render_markdown(brief)
    assert markdown.startswith("# Repair Brief: iPhone 12")
    assert "## Safety warnings" in markdown
    assert "deterministic-fallback" in markdown


def test_store_round_trip(tmp_path: Path):
    db = tmp_path / "test.db"
    brief = build_fallback_brief(
        "Redmi Note 12", "boot loop", _texts(), Language.PT
    )
    brief_id = save_brief(brief, session_id="test-session", db_path=db)
    assert brief_id >= 1
    rows = list_briefs(db_path=db)
    assert rows[0]["device"] == "Redmi Note 12"
    assert rows[0]["session_id"] == "test-session"
    loaded = get_brief(brief_id, db_path=db)
    assert loaded is not None
    assert loaded.symptom == "boot loop"
    assert get_brief(99999, db_path=db) is None


def test_cli_offline_brief_json(tmp_path: Path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = main(
        [
            "brief",
            "--device", "Samsung Galaxy A54",
            "--symptom", "not charging",
            "--sample", "samsung-not-charging.md",
            "--offline",
            "--format", "json",
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    payload = json.loads(out[out.index("{"):])
    assert payload["device"] == "Samsung Galaxy A54"
    assert payload["generated_by"] == "deterministic-fallback"


def test_cli_brief_without_source_is_usage_error():
    code = main(["brief", "--device", "X", "--symptom", "Y", "--offline"])
    assert code == 4


def test_cli_samples(capsys):
    assert main(["samples"]) == 0
    assert "samsung-not-charging.md" in capsys.readouterr().out
