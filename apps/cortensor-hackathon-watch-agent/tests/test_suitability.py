from hackathon_watch.models import HackathonEntry
from hackathon_watch.suitability import (
    build_classify_messages, rule_screen)


def _entry(name, notes=""):
    return HackathonEntry(name=name, url="https://example.test/x",
                          source="devfolio", notes=notes)


def test_student_only_is_not_suitable():
    v = rule_screen(_entry("CRC Hacks", "students only, online"))
    assert v.label == "not-suitable"
    assert "student" in v.reason.lower()


def test_fee_is_not_suitable():
    v = rule_screen(_entry("Some Hack", "entry fee $20"))
    assert v.label == "not-suitable"


def test_llm_direction_is_preliminary():
    v = rule_screen(_entry("Build Your First AI App",
                           "LLM chatbot hackathon, online, free"))
    assert v.label == "preliminary"


def test_no_signal_is_unsure():
    v = rule_screen(_entry("Health Hackathon 3.0"))
    assert v.label == "unsure"


def test_verdict_always_needs_human_confirmation():
    for entry in [_entry("CRC Hacks", "students only"),
                  _entry("AI Agent Jam", "Agent hackathon, online")]:
        assert rule_screen(entry).needs_human_confirmation is True


def test_classify_prompt_is_short():
    messages = build_classify_messages(_entry("AI Agent Jam", "online"))
    joined = " ".join(m["content"] for m in messages)
    assert len(joined.split()) < 200
    assert "preliminary" in joined and "not-suitable" in joined
