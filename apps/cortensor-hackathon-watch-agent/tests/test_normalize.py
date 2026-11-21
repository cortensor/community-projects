from hackathon_watch.normalize import (
    entry_key, humanize_slug, normalize_name, normalize_url)


def test_normalize_url_strips_www_trailing_slash_and_utm():
    assert normalize_url("https://www.DoraHacks.io/hackathon/2418/detail/?utm_source=x") == \
        "https://dorahacks.io/hackathon/2418/detail"


def test_normalize_url_adds_scheme():
    assert normalize_url("dorahacks.io/hackathon/abc") == \
        "https://dorahacks.io/hackathon/abc"


def test_normalize_name_case_and_punctuation():
    assert normalize_name("Cortensor Hackathon #5!") == "cortensor hackathon 5"
    assert normalize_name("  Agent  Harness ") == "agent harness"


def test_entry_key_prefers_url():
    assert entry_key("https://example.com/a/", "Whatever") == "url:https://example.com/a"
    assert entry_key("", "Some Name") == "name:some name"


def test_humanize_slug():
    assert humanize_slug("the-open-league-hackathon") == "The Open League Hackathon"
    assert humanize_slug("hackathon-galactica-wdk-2026-01") == "Hackathon Galactica Wdk 2026 01"
