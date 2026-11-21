import httpx

from hackathon_watch.check import run_check, seed_memory_from_baseline
from hackathon_watch.config import resolve_provider
from hackathon_watch.llm_client import DirectClient
from hackathon_watch.memory import WatchMemory
from conftest import FakeClock, llm_stub_handler

REPO_BASELINE = "data"

DORAHACKS_HTML = """
<html><body>
<a href="/hackathon/build-and-brew">Visit</a>
<a href="/hackathon/ai-agent-summit-2026">Visit</a>
</body></html>
"""

DEVFOLIO_HTML = """
<html><body>
<a href="https://health-hackathon.devfolio.co/"><h3>Health Hackathon 3.0</h3></a>
<a href="https://ai-agent-jam.devfolio.co/"><h3>AI Agent Jam</h3></a>
</body></html>
"""

KAGGLE_WALL = "<html><head><base href=\"https://www.google.com/recaptcha/challengepage/\"></head></html>"


def _overrides():
    return {"dorahacks": DORAHACKS_HTML, "devfolio": DEVFOLIO_HTML,
            "kaggle": KAGGLE_WALL}


def test_seed_memory_from_baseline(tmp_state):
    mem = WatchMemory(tmp_state / "memory.json")
    seeded = seed_memory_from_baseline(mem, REPO_BASELINE)
    assert seeded >= 165
    assert len(mem) == seeded


def test_check_reports_only_new_entries(tmp_state):
    mem = WatchMemory(tmp_state / "memory.json")
    report = run_check(["dorahacks", "devfolio", "kaggle"], mem,
                       baseline_dir=REPO_BASELINE,
                       html_overrides=_overrides())
    assert report.seeded_from_baseline is True
    # DoraHacks fixture: build-and-brew is a slug from the live homepage
    # but is NOT in the baseline; ai-agent-summit-2026 is new too.
    # Devfolio fixture: Health Hackathon 3.0 is new; AI Agent Jam is new.
    new_names = {e.name for e in report.new_entries}
    assert "Ai Agent Summit 2026" in new_names
    assert "AI Agent Jam" in new_names
    # Kaggle is honestly unavailable, not faked.
    kaggle = [s for s in report.sources if s.source == "kaggle"][0]
    assert kaggle.status == "unavailable"
    assert "reCAPTCHA" in kaggle.detail
    # Second run: nothing new, nothing re-alerted.
    report2 = run_check(["dorahacks", "devfolio", "kaggle"], mem,
                        baseline_dir=REPO_BASELINE,
                        html_overrides=_overrides())
    assert report2.new_entries == []
    assert report2.alerts == []


def test_check_alerts_only_preliminary(tmp_state):
    mem = WatchMemory(tmp_state / "memory.json")
    report = run_check(["devfolio"], mem, baseline_dir=None,
                       html_overrides={"devfolio": DEVFOLIO_HTML})
    # AI Agent Jam matches the LLM/Agent direction -> preliminary alert.
    assert any(e.name == "AI Agent Jam" for e in report.alerts)
    # Health Hackathon 3.0 has no direction signal -> unsure, no alert.
    assert not any(e.name == "Health Hackathon 3.0" for e in report.alerts)
    assert report.model_calls == 0  # rules only, no live classify


def test_check_live_classify_uses_stub_model(tmp_state):
    clock = FakeClock()
    provider = resolve_provider("openai-compatible")
    client = DirectClient(provider, min_interval_sec=0,
                          transport=httpx.MockTransport(llm_stub_handler()),
                          sleep=clock.sleep, clock=clock.time)
    mem = WatchMemory(tmp_state / "memory.json")
    report = run_check(["devfolio"], mem, baseline_dir=None,
                       live_classify=True, max_model_calls=5, client=client,
                       html_overrides={"devfolio": DEVFOLIO_HTML})
    # Only the unsure entry (Health Hackathon 3.0) costs a model call.
    assert report.model_calls == 1
    assert report.model_tokens == 120
    verdict = report.verdicts
    assert any(v.label == "preliminary" for v in verdict.values())
