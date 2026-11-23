"""Offline tests for deterministic fact extraction (no model needed)."""

from fixbrief.facts import extract_facts, infer_difficulty
from fixbrief.sources import list_samples, load_sample


def test_samples_exist_and_load():
    names = list_samples()
    assert "samsung-not-charging.md" in names
    assert "iphone-black-screen.md" in names
    assert "redmi-boot-loop.md" in names
    text = load_sample("samsung-not-charging.md")
    assert "not charging" in text.lower()


def test_extract_facts_from_sample():
    facts = extract_facts(load_sample("samsung-not-charging.md"))
    assert facts.char_count > 500
    assert "not charging" in facts.symptom_hints
    assert any("cable" in c.lower() for c in facts.causes)
    assert len(facts.steps) >= 6
    assert "multimeter" in facts.tools
    assert any("swollen" in w.lower() for w in facts.warnings)
    assert 40 in facts.time_hints_minutes or 20 in facts.time_hints_minutes


def test_headings_and_tools_do_not_leak_into_causes_or_steps():
    facts = extract_facts(load_sample("samsung-not-charging.md"))
    assert not any(c.startswith("#") for c in facts.causes)
    assert not any("Common causes" in c for c in facts.causes)
    # Steps are the numbered diagnostic procedure, not tool bullets.
    assert facts.steps[0].startswith("Try a known-good charger")
    assert "Tweezers" not in facts.steps
    assert "USB current meter" not in facts.steps
    # Tool bullets land in tools with their full names.
    assert any("USB current meter" in t for t in facts.tools)


def test_infer_difficulty_board_work_is_professional():
    facts = extract_facts("Microsoldering repair. Solder the charging IC.")
    assert infer_difficulty(facts) == "professional"


def test_infer_difficulty_software_is_easy():
    facts = extract_facts("Restart the phone and check settings. Software fix.")
    assert infer_difficulty(facts) == "easy"


def test_extract_facts_empty_text():
    facts = extract_facts("")
    assert facts.char_count == 0
    assert facts.steps == []
    assert facts.causes == []
