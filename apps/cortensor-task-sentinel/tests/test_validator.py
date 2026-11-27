"""Unit tests for Cortensor Sentinel Task Validator."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest

from cortensor_validator.attestation import AttestationSigner
from cortensor_validator.openminion_agent import (
    CortensorSentinel,
    audit_code_safety,
    create_attestation_receipt,
    execute_test_case,
)
from cortensor_validator.sentinel import verify_file
from cortensor_validator.verifier import verify_code_safety


def test_code_safety_accepts_clean_code() -> None:
    code = "def solution(x: int) -> int:\n    return x * 2\n"
    res = verify_code_safety(code)
    assert res.valid is True
    assert len(res.violations) == 0
    assert res.ast_nodes_scanned > 0


def test_code_safety_rejects_forbidden_imports() -> None:
    code = "import os\ndef solution(x: int) -> int:\n    return x\n"
    res = verify_code_safety(code)
    assert res.valid is False
    assert any("Forbidden import: 'os'" in v for v in res.violations)


def test_code_safety_rejects_forbidden_builtins() -> None:
    code = "def solution(x: str) -> None:\n    eval(x)\n"
    res = verify_code_safety(code)
    assert res.valid is False
    assert any("Forbidden builtin call: 'eval()'" in v for v in res.violations)


def test_code_safety_rejects_obfuscated_dynamic_imports() -> None:
    code = "def solution(x: str) -> None:\n    getattr(__builtins__, 'eval')(x)\n"
    res = verify_code_safety(code)
    assert res.valid is False
    assert any("Forbidden builtin call: 'getattr()'" in v or "Forbidden variable access: '__builtins__'" in v for v in res.violations)


def test_code_safety_rejects_sandbox_breakout_attributes() -> None:
    code = "def solution(x: int) -> int:\n    classes = ().__class__.__bases__[0].__subclasses__()\n    return len(classes)\n"
    res = verify_code_safety(code)
    assert res.valid is False
    assert any("Forbidden attribute access: '__class__'" in v or "Forbidden attribute access: '__subclasses__'" in v for v in res.violations)


@pytest.mark.parametrize(
    "body",
    [
        "return '{0.__class__}'.format(x)",
        "g = (g.gi_frame.f_back for _ in [1])\n    return list(g)",
        "return globals()",
        "return int.__mro__",
    ],
)
def test_code_safety_rejects_frame_format_and_scope_escapes(body: str) -> None:
    res = verify_code_safety(f"def solution(x):\n    {body}\n")
    assert res.valid is False


def test_code_safety_rejects_syntax_errors() -> None:
    code = "def solution(x:\n    return x\n"
    res = verify_code_safety(code)
    assert res.valid is False
    assert any("SyntaxError" in v for v in res.violations)


def test_attestation_signing_and_verification() -> None:
    signer = AttestationSigner(validator_id="val-test-01")
    receipt = signer.sign(task_id="task-123", passed=True)
    assert receipt.task_id == "task-123"
    assert receipt.validator_id == "val-test-01"
    assert receipt.passed is True
    assert len(receipt.signature) == 64
    assert signer.verify(receipt) is True


def test_openminion_tool_audit_safety() -> None:
    clean = audit_code_safety("def solution(x: int) -> int:\n    return x + 1\n")
    assert clean["valid"] is True
    assert len(clean["violations"]) == 0

    bad = audit_code_safety("import subprocess\n")
    assert bad["valid"] is False
    assert len(bad["violations"]) > 0


def test_openminion_tool_execute_test_case() -> None:
    code = "def solution(x: int) -> int:\n    return x ** 2\n"
    res = execute_test_case(code, 4, 16)
    assert res["passed"] is True
    assert res["actual_output"] == 16


def test_openminion_agent_instantiation() -> None:
    sentinel = CortensorSentinel(validator_id="val-node-01")
    agent = sentinel.create_agent()
    assert agent.name == "CortensorSentinel-val-node-01"
    assert "audit_code_safety" in agent.tools
    assert "execute_test_case" in agent.tools
    assert "create_attestation_receipt" in agent.tools


def test_sentinel_end_to_end_verification() -> None:
    sentinel = CortensorSentinel(validator_id="val-node-01")
    code = "def solution(x: int) -> int:\n    return x * 3\n"
    passed, receipt = sentinel.verify_submission(
        task_id="task-triple-5",
        code=code,
        test_input=5,
        expected_output=15,
    )
    assert passed is True
    assert receipt.passed is True
    assert sentinel.signer.verify(receipt) is True


def test_environment_variable_configuration(monkeypatch) -> None:
    monkeypatch.setenv("CORTENSOR_VALIDATOR_ID", "val-env-override-99")
    monkeypatch.setenv("CORTENSOR_EPOCH", "42")

    signer = AttestationSigner()
    assert signer.validator_id == "val-env-override-99"
    assert signer.current_epoch == 42

    sentinel = CortensorSentinel()
    assert sentinel.validator_id == "val-env-override-99"
    assert sentinel.epoch == 42


def test_cli_verify_file() -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
        tmp.write("def solution(n: int) -> int:\n    return n + 10\n")
        tmp_path = Path(tmp.name)

    try:
        ret = verify_file(
            code_path=tmp_path,
            task_id="test-file-task",
            test_input=5,
            expected_output=15,
            verbose=False,
        )
        assert ret == 0
    finally:
        tmp_path.unlink(missing_ok=True)


def test_execute_test_case_timeout() -> None:
    # Bounded infinite loop is killed by the parent wall clock or the child CPU limit
    infinite_loop_code = "def solution(n: int) -> int:\n    while True:\n        pass\n"
    res = execute_test_case(infinite_loop_code, 5, 5, timeout_seconds=0.2)
    assert res["passed"] is False
    assert "timed out" in res["error"].lower() or "killed" in res["error"].lower()


def test_bare_except_loop_cannot_swallow_the_timeout() -> None:
    # A timer exception inside the same process is swallowed by this code and the
    # loop never ends. The child process is killed from outside instead.
    code = (
        "def solution(n):\n"
        "    while True:\n"
        "        try:\n"
        "            while True:\n"
        "                pass\n"
        "        except:\n"
        "            pass\n"
    )
    t0 = time.perf_counter()
    res = execute_test_case(code, 1, 1, timeout_seconds=0.5)
    assert time.perf_counter() - t0 < 5.0
    assert res["passed"] is False
    assert "timed out" in res["error"] or "killed" in res["error"]


def test_memory_bomb_fails_the_case_and_leaves_the_parent_alive() -> None:
    code = "def solution(n):\n    return len([0] * (10 ** 10))\n"
    res = execute_test_case(code, 1, 1, timeout_seconds=2.0)
    assert res["passed"] is False
    assert "MemoryError" in res["error"] or "killed" in res["error"]


def test_cli_verify_file_json(capsys) -> None:
    import json

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
        tmp.write("def solution(n: int) -> int:\n    return n * 4\n")
        tmp_path = Path(tmp.name)

    try:
        ret = verify_file(
            code_path=tmp_path,
            task_id="test-json-task",
            test_input=3,
            expected_output=12,
            json_mode=True,
        )
        assert ret == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["task_id"] == "test-json-task"
        assert data["status"] == "CERTIFIED"
        assert data["passed"] is True
        assert len(data["signature"]) == 64
    finally:
        tmp_path.unlink(missing_ok=True)


def test_query_hosted_portal_without_key(monkeypatch) -> None:
    from cortensor_validator.openminion_agent import query_hosted_portal, verify_via_hosted_portal

    monkeypatch.delenv("CORTENSOR_API_KEY", raising=False)
    res = query_hosted_portal(api_key=None)
    assert res["connected"] is False

    tool_res = verify_via_hosted_portal("def solution(x: int) -> int: return x * 2", 3, 6)
    assert tool_res["portal"]["connected"] is False
    assert tool_res["result"]["passed"] is True


def _mock_portal_up(monkeypatch) -> None:
    import urllib.request

    class MockResponse:
        status = 200

        def read(self):
            return b'{"data": [{"id": "oss-20b"}]}'

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout: MockResponse())


def test_query_hosted_portal_mock_connected(monkeypatch) -> None:
    from cortensor_validator.openminion_agent import query_hosted_portal

    _mock_portal_up(monkeypatch)
    res = query_hosted_portal(api_key="ct-test-api-key")
    assert res["connected"] is True
    assert res["models"] == ["oss-20b"]
    assert "passed" not in res and "data" not in res


def test_reachable_portal_does_not_certify_wrong_code(monkeypatch) -> None:
    """A reachable Portal used to make verify_submission sign passed=True for any safe code."""
    _mock_portal_up(monkeypatch)
    sentinel = CortensorSentinel(api_key="ct-test-api-key")
    passed, receipt = sentinel.verify_submission(
        task_id="task-wrong-answer",
        code="def solution(x: int) -> int: return x + 1",
        test_input=1,
        expected_output=1,
        use_hosted=True,
    )
    assert passed is False
    assert receipt.passed is False
    assert sentinel.last_mode == "local, portal reachable"


def test_live_verdict_comes_from_tool_results() -> None:
    from cortensor_validator.live_agent import _verdict_from_tools

    code = "def solution(n): return n\n"
    audit_ok = ("audit_code_safety", {"valid": True, "violations": [], "_code": code})
    assert _verdict_from_tools([], code) == (False, "model never called audit_code_safety")
    blocked = [("audit_code_safety", {"valid": False, "violations": ["import os"], "_code": code})]
    assert _verdict_from_tools(blocked, code)[0] is False
    assert _verdict_from_tools([audit_ok], code) == (False, "model never called execute_test_case")
    ok = [audit_ok, ("execute_test_case", {"passed": True, "actual_output": 55, "_code": code})]
    assert _verdict_from_tools(ok, code)[0] is True
    # A receipt the model signed with passed=True does not override a failed test.
    bad = [
        audit_ok,
        ("execute_test_case", {"passed": False, "actual_output": 2, "expected_output": 1, "_code": code}),
        ("create_attestation_receipt", {"passed": True}),
    ]
    assert _verdict_from_tools(bad, code)[0] is False


def test_live_verdict_rejects_model_rewritten_code() -> None:
    """Seen in a real run: the model dropped `import os`, re-audited and tested the rewrite."""
    from cortensor_validator.live_agent import _verdict_from_tools

    submitted = "import os\ndef solution(n):\n    os.system('id')\n    return n\n"
    rewritten = "def solution(n):\n    return n\n"
    calls = [
        ("audit_code_safety", {"valid": False, "violations": ["Forbidden import: 'os'"], "_code": submitted}),
        ("audit_code_safety", {"valid": True, "violations": [], "_code": rewritten}),
        ("execute_test_case", {"passed": True, "actual_output": 10, "_code": rewritten}),
    ]
    passed, reason = _verdict_from_tools(calls, submitted)
    assert passed is False
    assert "other than the submission" in reason
    # Reformatting is not a rewrite: a blank line and no trailing newline still count as the submission.
    reflowed = "import os\n\ndef solution(n):\n    os.system('id')\n    return n"
    calls_fmt = [("audit_code_safety", {"valid": False, "violations": ["Forbidden import: 'os'"], "_code": reflowed})]
    assert _verdict_from_tools(calls_fmt, submitted)[1].startswith("audit blocked")
    # Even without the rewrite, a later passing audit cannot undo a blocked one.
    calls2 = [calls[0], ("audit_code_safety", {"valid": True, "violations": [], "_code": submitted})]
    assert _verdict_from_tools(calls2, submitted)[0] is False


def test_live_config_sets_channel_and_requires_model(tmp_path, monkeypatch) -> None:
    import json
    import pytest
    from cortensor_validator.live_agent import write_agent_config

    monkeypatch.delenv("SENTINEL_MODEL", raising=False)
    with pytest.raises(ValueError):
        write_agent_config("local", tmp_path)
    monkeypatch.setenv("SENTINEL_MODEL", "some-model")
    cfg = json.loads(write_agent_config("local", tmp_path).read_text())
    assert cfg["agents"]["sentinel"]["default_channel"] == "console"
    assert cfg["providers"]["openai"]["model"] == "some-model"
    portal = json.loads(write_agent_config("portal", tmp_path).read_text())
    assert portal["providers"]["openai"]["base_url"] == "https://api.cortensor.app/v1"
    assert portal["providers"]["openai"]["api_key_env"] == "CORTENSOR_API_KEY"


def test_portal_config_disables_heavy_preturn_overhead(tmp_path) -> None:
    import json
    from cortensor_validator.live_agent import write_agent_config

    portal = json.loads(write_agent_config("portal", tmp_path).read_text())
    assert portal["runtime"]["memory_enabled"] is False
    assert portal["runtime"]["brain_turn_timeout_seconds"] == 900
    assert portal["runtime"]["chat_turn_timeout_seconds"] == 900
    assert portal["brain"]["auto_fact_extraction"]["enabled"] is False
    assert portal["brain"]["reflection"]["enabled"] is False
    assert portal["brain"]["adaptive_budget"]["idle_timeout_s"] == 900
    assert portal["agents"]["sentinel"]["default_channel"] == "console"
    assert "thinking" not in portal["agents"]["sentinel"]


def test_live_demo_portal_retries_transient_provider_error(monkeypatch, tmp_path) -> None:
    from cortensor_validator import live_agent as la
    from cortensor_validator import openminion_agent as om
    from cortensor_validator import sentinel as sen

    monkeypatch.setenv("SENTINEL_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("CORTENSOR_API_KEY", "ct-test-key")
    monkeypatch.setattr(
        om,
        "query_hosted_portal",
        lambda base_url=None: {"connected": True, "models": ["oss-20b"]},
    )
    monkeypatch.setattr(sen.time, "sleep", lambda _s: None)

    calls = {"count": 0}

    def fake_run_live_task(config_path, task_id, code, test_input, expected_output, timeout_seconds=400.0):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("PROVIDER_ERROR: HTTP 502: transient router pool error")
        if task_id == "task-fibonacci-10":
            return la.LiveResult(
                task_id=task_id,
                passed=True,
                reason="test passed (output 55)",
                model_text="ok",
                tool_calls=[("audit_code_safety", {"valid": True})],
                stats={"llm_calls": 5, "input_tokens": 100, "output_tokens": 20},
                llm_calls_by_purpose={"entry": 1, "act": 4},
            )
        return la.LiveResult(
            task_id=task_id,
            passed=False,
            reason="audit blocked: Forbidden import: 'os'",
            model_text="blocked",
            tool_calls=[("audit_code_safety", {"valid": False})],
            stats={"llm_calls": 3, "input_tokens": 80, "output_tokens": 15},
            llm_calls_by_purpose={"entry": 1, "act": 2},
        )

    monkeypatch.setattr(la, "run_live_task", fake_run_live_task)
    rc = sen.run_live_demo("portal")
    assert rc == 0
    assert calls["count"] == 3
