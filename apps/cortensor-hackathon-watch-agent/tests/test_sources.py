import pytest

from hackathon_watch.sources import (
    SourceUnavailable, fetch_source, parse_devfolio, parse_dorahacks,
    parse_kaggle)


def test_parse_dorahacks_fixture(fixtures_dir):
    html = (fixtures_dir / "dorahacks-home-sample.html").read_text()
    entries = parse_dorahacks(html)
    assert len(entries) == 5
    slugs = {e.url.rsplit("/", 1)[-1] for e in entries}
    assert slugs == {"build-and-brew", "coinmarketcap-api-202609",
                     "hackathon-galactica-wdk-2026-01", "mozilla-devs-wilding",
                     "the-open-league-hackathon"}
    # Names come from the slug on this JS-rendered page — marked as such.
    assert all(e.name_source == "slug" for e in entries)
    assert all(e.source == "dorahacks" for e in entries)


def test_parse_devfolio_fixture(fixtures_dir):
    html = (fixtures_dir / "devfolio-list-sample.html").read_text()
    entries = parse_devfolio(html)
    assert len(entries) == 3
    names = {e.name for e in entries}
    assert "DevNexus 2.0" in names
    assert "Lean In Hacks 8.0" in names
    assert "CODEFESTTHON 2026" in names
    assert all(e.name_source == "page" for e in entries)
    assert all(e.url.startswith("https://") and ".devfolio.co/" in e.url
               for e in entries)
    # Deadline/prize are NOT on the list page — never guessed.
    assert all(e.deadline is None and e.prize is None for e in entries)


def test_parse_kaggle_recaptcha_is_unavailable(fixtures_dir):
    html = (fixtures_dir / "kaggle-recaptcha-sample.html").read_text()
    assert "recaptcha" in html.lower()
    with pytest.raises(SourceUnavailable, match="reCAPTCHA"):
        parse_kaggle(html)


def test_fetch_source_unknown():
    with pytest.raises(ValueError, match="unknown source"):
        fetch_source("not-a-source")


def test_fetch_source_fixture_override(fixtures_dir):
    html = (fixtures_dir / "devfolio-list-sample.html").read_text()
    outcome = fetch_source("devfolio", html_override=html)
    assert outcome.source == "devfolio"
    assert len(outcome.entries) == 3
    assert outcome.detail == "fixture HTML"
