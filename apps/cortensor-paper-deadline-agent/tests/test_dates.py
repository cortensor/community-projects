"""Date parsing: the dirty free-text cells."""

from datetime import date

from paper_watch.dates import earliest_future, parse_deadline_cell

T = date(2026, 11, 17)


def test_iso_multi_track_earliest_future():
    entries = parse_deadline_cell("2026-10-25 (Long); 2026-11-16 (Short)")
    assert [e.date.isoformat() for e in entries] == ["2026-10-25", "2026-11-16"]
    assert entries[1].track == "Short"
    # both in the past relative to T -> None
    assert earliest_future("2026-10-25 (Long); 2026-11-16 (Short)", T) is None


def test_earliest_future_picks_first_future_track():
    got = earliest_future("2026-11-20 (Long); 2026-12-05 (Short)", T)
    assert got is not None and got.date == date(2026, 11, 20) and got.track == "Long"


def test_english_month_format():
    got = earliest_future("Dec 8, 2026 (AoE, firm)", T)
    assert got is not None and got.date == date(2026, 12, 8)
    assert earliest_future("Mar 30, 2026 (AoE, firm)", T) is None  # past


def test_day_month_year_format():
    got = earliest_future("8 Dec 2026", T)
    assert got is not None and got.date == date(2026, 12, 8)


def test_rolling_and_tbd_yield_nothing():
    assert parse_deadline_cell("rolling - no fixed deadline (journal submissions)") == []
    assert parse_deadline_cell("TBD") == []
    assert parse_deadline_cell("") == []
    assert parse_deadline_cell(None) == []
    assert earliest_future("ARR submission deadline: 2027-01-04; ACL commitment deadline: TBD", T).date == date(2027, 1, 4)


def test_invalid_calendar_date_is_skipped_not_corrected():
    assert parse_deadline_cell("2026-02-30") == []


def test_semicolon_separated_fixed_dates():
    got = earliest_future("2026-11-30; 2026-12-30", T)
    assert got is not None and got.date == date(2026, 11, 30)
