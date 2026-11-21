from pathlib import Path

from hackathon_watch.baseline import load_baseline, parse_baseline_text

REPO = Path(__file__).resolve().parents[1]


def test_open_list_parses_100_main_plus_supplement():
    text = (REPO / "data" / "open-list-20261116.md").read_text()
    entries = parse_baseline_text(text)
    # 100 main entries + K/D supplementary entries (Kaggle + global).
    assert len(entries) >= 130
    names = [e.name for e in entries]
    assert "2026华为开发者大赛·小红书Skill创新赛道" in names
    assert "Meta VR Start Developer Competition 2026" in names
    assert "Google - The Gemma 4 Developer Agent Competition" in names


def test_full_recheck_names_not_truncated():
    text = (REPO / "data" / "full-recheck-20261116.md").read_text()
    entries = parse_baseline_text(text)
    assert len(entries) == 19
    names = [e.name for e in entries]
    assert "Google - Agent Harness on Physical-Engineering's Last Exam" in names
    assert "Cortensor Hackathon #5" in names


def test_verified_file_headings_parse():
    text = (REPO / "data" / "full-recheck-20261116-verified.md").read_text()
    entries = parse_baseline_text(text)
    assert len(entries) == 19
    by_name = {e.name: e for e in entries}
    assert by_name["Cortensor Hackathon #5"].url == \
        "https://dorahacks.io/hackathon/2418/detail"


def test_load_baseline_dedupes_aggregator_urls():
    entries, stats = load_baseline(REPO / "data")
    # Tracker states 171 open; we parse 177 lines and dedupe to ~170
    # (one same-name to_verify duplicate survives by design).
    assert stats["parsed"] == 177
    assert 165 <= stats["deduped"] <= 171
    # Distinct events sharing one aggregator URL must survive.
    aicpt = [e for e in entries if "aicpt-memo.cn" in e.url]
    assert len(aicpt) >= 20
    assert len({e.name for e in aicpt}) == len(aicpt)


def test_no_bogus_section_header_entries():
    entries, _ = load_baseline(REPO / "data")
    assert not any("截止" in e.name and len(e.name) < 12 for e in entries)
    assert not any(e.name.startswith("月") for e in entries)
