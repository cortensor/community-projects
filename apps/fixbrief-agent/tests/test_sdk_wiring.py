"""SDK wiring tests using the credential-free echo provider.

Echo exercises config, sessions, and tool registration plumbing. It is
NOT a model: echo replies cannot validate as a RepairBrief, and these
tests assert that failure is surfaced honestly (exit code 2) instead of
being disguised as a model result. Real model runs are covered by the
recorded demo (Ollama) and the live receipt in outputs/.
"""

import pytest

from fixbrief.agent import (
    BriefError,
    get_source_facts,
    lookup_term,
    run_model_brief,
)
from fixbrief.config import ensure_config
from fixbrief.models import Language


def test_tools_are_callable_directly():
    # Decorated tools remain plain callables for direct unit testing.
    payload = get_source_facts("sample", "samsung-not-charging.md")
    assert "not charging" in payload
    assert lookup_term("battery", "es") == "batería"
    assert "unsupported language" in lookup_term("battery", "xx")


def test_echo_config_is_created():
    path = ensure_config("echo")
    assert path.exists()


def test_echo_model_brief_fails_validation_honestly():
    ensure_config("echo")
    with pytest.raises(BriefError) as excinfo:
        run_model_brief(
            device="Samsung Galaxy A54",
            symptom="not charging",
            sources=[("sample", "samsung-not-charging.md")],
            language=Language.EN,
            provider="echo",
            session_id="pytest-echo",
            timeout_seconds=120,
            persist=False,
        )
    # Echo cannot produce schema-valid JSON: validation error, exit 2.
    assert excinfo.value.exit_code == 2
