"""Store: loading, window filtering, status passthrough, unclear handling."""

from datetime import date

from conftest import TODAY
from paper_watch.store import DATE_UNCLEAR, VenueStore


def test_load_counts(store):
    # 4 dated (CVPR, FAKE-abstract, NEXT, ENG) + 2 fixed (JTEST, LTEST)
    assert len(store.deadlines) == 6
    # OLD (past only), TBDX (TBD), JROLL (rolling, no fixed date)
    assert len(store.unclear) == 3
    assert all(d.status == DATE_UNCLEAR for d in store.unclear)


def test_upcoming_window_120_days(store):
    rows = store.upcoming(120, TODAY)
    abbrs = [d.abbreviation for d in rows]
    # CVPR 2026-11-27, JTEST 2026-11-30, FAKE abstract 2026-12-01,
    # ENG 2026-12-08, LTEST 2026-12-15, NEXT 2027-01-15
    assert abbrs == ["CVPR", "JTEST", "FAKE", "ENG", "LTEST", "NEXT"]
    assert rows[0].deadline_kind == "full" and rows[0].track == "Long"
    assert rows[2].deadline_kind == "abstract"  # FAKE: only abstract is future


def test_upcoming_window_short_excludes_later(store):
    rows = store.upcoming(10, TODAY)
    assert [d.abbreviation for d in rows] == ["CVPR"]


def test_status_is_never_upgraded(store):
    by_abbr = {d.abbreviation: d for d in store.deadlines}
    assert by_abbr["NEXT"].status == "cycle_not_announced"
    assert by_abbr["CVPR"].status == "verified"
    assert by_abbr["ENG"].status == "verified"


def test_one_line_always_carries_status(store):
    for d in store.deadlines:
        assert f"[{d.status}]" in d.one_line()
        assert d.deadline_date.isoformat() in d.one_line()


def test_by_abbreviation_finds_unclear_too(store):
    assert store.by_abbreviation("old").status == DATE_UNCLEAR
    assert store.by_abbreviation("cvpr").full_name.startswith("IEEE Conference")
    assert store.by_abbreviation("nope") is None


def test_memory_key_is_stable(store):
    d = store.by_abbreviation("CVPR")
    assert d.memory_key == "CVPR|2026-11-27|full"


def test_real_data_spot_counts():
    # The real tables: 390 conf + 295 journals + 24 law rows load cleanly.
    from pathlib import Path

    real = Path(__file__).resolve().parent.parent / "data"
    if not (real / "deadlines-all-conferences.csv").exists():
        import pytest

        pytest.skip("real data/ not copied yet")
    store = VenueStore.load(real, today=TODAY)
    # 709 rows, minus 1 exact cross-file duplicate (CLSR in journals + law)
    assert len(store.deadlines) + len(store.unclear) == 709 - 1
    rows = store.upcoming(120, TODAY)
    # verified by running the loader: 60 conf (59 full + 1 abstract-only),
    # 23 journals (incl. "Neural Networks", recovered from an empty-abbr row),
    # 1 law (Digital Society; CLSR is deduped to its journal row)
    assert len(rows) == 84
    from collections import Counter

    assert Counter(d.kind for d in rows) == {"conference": 60, "journal": 23, "law": 1}
