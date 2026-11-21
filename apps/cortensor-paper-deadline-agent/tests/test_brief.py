"""Topics + brief: matching, template honesty, no invented venues."""

from conftest import TODAY
from paper_watch.brief import (
    build_template_brief,
    check_honesty,
    render_brief,
)
from paper_watch.topics import match_topic


def test_chinese_topic_matches_field(store):
    rows = store.upcoming(120, TODAY)
    got = match_topic("人工智能", rows)
    assert [d.abbreviation for d in got] == ["JTEST", "FAKE"]  # earliest first


def test_english_topic_matches_full_name(store):
    rows = store.upcoming(120, TODAY)
    got = match_topic("vision", rows)
    assert [d.abbreviation for d in got] == ["CVPR"]


def test_no_match_is_empty_not_invented(store):
    rows = store.upcoming(120, TODAY)
    assert match_topic("量子纠错", rows) == []
    brief = build_template_brief("量子纠错", [])
    assert "No upcoming submission deadline was found" in brief.paragraphs[0]
    assert brief.deadlines == []


def test_template_brief_names_nearest_and_a_level(store):
    rows = store.upcoming(120, TODAY)
    matched = match_topic("人工智能", rows)
    brief = build_template_brief("人工智能", matched)
    assert brief.synthesis_source == "template"
    assert brief.nearest.abbreviation == "JTEST"  # 2026-11-30 < FAKE 2026-12-01
    assert {d.abbreviation for d in brief.a_level} == {"JTEST"}


def test_rendered_brief_passes_honesty(store):
    rows = store.upcoming(120, TODAY)
    brief = build_template_brief("人工智能", match_topic("人工智能", rows))
    text = render_brief(brief)
    assert check_honesty(text, brief.deadlines) == []
    # status tags present on every deadline line
    for d in brief.deadlines:
        assert f"[{d.status}]" in text


def test_honesty_catches_verified_label_on_unverified_row(store):
    rows = store.upcoming(120, TODAY)
    nxt = next(d for d in rows if d.abbreviation == "NEXT")
    bad_text = "- NEXT [A] Next Cycle Conf — full deadline 2027-01-15 [verified] https://next.example"
    assert check_honesty(bad_text, [nxt]) != []


def test_honesty_does_not_false_positive_on_substring(store):
    # ICWSM's full name contains "AAAI", but the line belongs to ICWSM.
    # An unclear AAAI must not be flagged for ICWSM's line.
    from paper_watch.store import Deadline

    icwsm = Deadline(
        abbreviation="ICWSM", full_name="The International AAAI Conference on Web and Social Media",
        kind="conference", ccf_grade="B", field="人工智能",
        deadline_date=__import__("datetime").date(2027, 1, 15),
        deadline_kind="full", track="", timezone="AoE", status="verified",
        source_url="https://www.icwsm.org/", website="",
    )
    aaai_unclear = Deadline(
        abbreviation="AAAI", full_name="AAAI Conference on Artificial Intelligence",
        kind="conference", ccf_grade="A", field="人工智能",
        deadline_date=None, deadline_kind="unclear", track="", timezone="",
        status="date_unclear", source_url="", website="",
    )
    text = "- " + icwsm.one_line()
    assert check_honesty(text, [icwsm, aaai_unclear]) == []


def test_template_flags_unverified_dates(store):
    rows = store.upcoming(120, TODAY)
    matched = match_topic("机器学习", rows)  # NEXT, cycle_not_announced
    brief = build_template_brief("机器学习", matched)
    text = render_brief(brief)
    assert "NOT been re-verified" in text
    assert check_honesty(text, brief.deadlines) == []
