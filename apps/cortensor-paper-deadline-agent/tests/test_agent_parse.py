"""Agent reply parsing: prefix strip + JSON extraction + validation."""

from paper_watch.agent import BriefSynthesis, extract_json_object, parse_synthesis_reply


def test_extract_plain_json():
    assert extract_json_object('{"a": 1}') == {"a": 1}


def test_extract_strips_agent_prefix():
    # The SDK prefixes replies with "agent_id: ".
    text = 'paper-watch: {"answer": "4", "confidence": 0.9}'
    assert extract_json_object(text) == {"answer": "4", "confidence": 0.9}


def test_extract_ignores_surrounding_prose():
    text = 'Here is the result:\n{"answer": "4", "confidence": 0.9}\nHope that helps.'
    assert extract_json_object(text) == {"answer": "4", "confidence": 0.9}


def test_extract_returns_none_for_prose_only():
    assert extract_json_object("2+2 equals 4.") is None
    assert extract_json_object("") is None
    assert extract_json_object("paper-watch: 2+2 equals 4.") is None


def test_parse_synthesis_reply_validates():
    good = '{"paragraphs": ["Nearest is CVPR.", "A-level: CVPR."], "nearest_abbreviation": "CVPR", "a_level_abbreviations": ["CVPR"]}'
    parsed = parse_synthesis_reply("brief-writer: " + good)
    assert isinstance(parsed, BriefSynthesis)
    assert parsed.nearest_abbreviation == "CVPR"


def test_parse_synthesis_reply_rejects_bad_schema():
    assert parse_synthesis_reply('{"paragraphs": "not a list"}') is None
    assert parse_synthesis_reply('{"nearest_abbreviation": "CVPR"}') is None
