"""402 retry policy: parse Retry-after, retry only free-limit errors."""

from paper_watch.agent import is_free_limit_error, parse_retry_after_seconds, run_agent_with_retry


def test_parse_retry_after():
    assert parse_retry_after_seconds("HTTP 402: Free limit reached. Retry after 17s, or get a key") == 17.0
    assert parse_retry_after_seconds("nothing here") is None


def test_is_free_limit_error():
    assert is_free_limit_error(RuntimeError("openai request failed with HTTP 402: Free limit reached: 1 reply"))
    assert not is_free_limit_error(RuntimeError("openai request failed with HTTP 500"))
    assert not is_free_limit_error(ValueError("boom"))


class _FlakyAgent:
    def __init__(self, failures):
        self.failures = failures
        self.calls = 0

    def run(self, message, **kwargs):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("HTTP 402: Free limit reached: 1 reply every 45 seconds per IP. Retry after 0s")
        return f"ok after {self.calls} calls"


def test_retry_then_success(monkeypatch):
    import paper_watch.agent as agent_mod

    monkeypatch.setattr(agent_mod.time, "sleep", lambda s: None)
    flaky = _FlakyAgent(failures=2)
    assert run_agent_with_retry(flaky, "hi", timeout_seconds=10, max_retries=3) == "ok after 3 calls"
    assert flaky.calls == 3


def test_non_402_not_retried(monkeypatch):
    import paper_watch.agent as agent_mod

    monkeypatch.setattr(agent_mod.time, "sleep", lambda s: None)

    class _BadAgent:
        def __init__(self):
            self.calls = 0

        def run(self, message, **kwargs):
            self.calls += 1
            raise RuntimeError("HTTP 500 boom")

    bad = _BadAgent()
    try:
        run_agent_with_retry(bad, "hi", timeout_seconds=10, max_retries=3)
    except RuntimeError:
        pass
    assert bad.calls == 1
