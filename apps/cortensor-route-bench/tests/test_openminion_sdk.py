"""Deterministic OpenMinion 0.1.23 SDK surface and helper contract tests."""

import pytest
from openminion import Agent, AgentOutputValidationError, Handoff, MemoryBundle, subagent
from openminion.api.handoff import DelegatedMemoryReadRequest
from sophiagraph.models import MemoryNamespace

from cortensor_route_bench.models import detect_runtime_interception, parse_structured_reply
from cortensor_route_bench.probes import ProbeCheckOutput, json_schema_instruction, run_with_backoff
from cortensor_route_bench.tools import ALL_DIAGNOSTIC_TOOLS, evaluate_json_contract


def test_json_schema_instruction_embeds_model_schema() -> None:
    prompt = json_schema_instruction(ProbeCheckOutput, "Analyze system.")
    assert "sdk_version" in prompt
    assert "Analyze system." in prompt
    assert "Respond ONLY with a single raw JSON object" in prompt


def test_evaluate_json_contract_tool() -> None:
    from cortensor_route_bench.tools import capture_validated_contracts

    valid_json = '{"worker_role":"a","readiness":"READY","confidence":0.8,"key_findings":["ok"],"recommended_action":"go"}'
    with capture_validated_contracts() as captured:
        ok_res = evaluate_json_contract(valid_json, "WorkerEvaluation")
        bad_res = evaluate_json_contract("plain prose", "WorkerEvaluation")

    assert ok_res["valid"] is True
    assert bad_res["valid"] is False
    assert len(captured) == 1
    assert captured[0][0] == "WorkerEvaluation"
    assert captured[0][1]["recommended_action"] == "go"


def test_all_diagnostic_tools_carry_read_only_tool_decl() -> None:
    for fn in ALL_DIAGNOSTIC_TOOLS:
        decl = getattr(fn, "tool_decl", None)
        assert decl is not None
        assert decl.name


def test_handoff_duplicate_names_fail_fast() -> None:
    a1 = Agent(name="peer_a", instructions="A")
    a2 = Agent(name="peer_b", instructions="B")
    with pytest.raises(ValueError, match="duplicate Handoff"):
        Agent(
            name="coord",
            instructions="Coord",
            handoffs=[
                Handoff(target=a1, name="transfer_to_same"),
                Handoff(target=a2, name="transfer_to_same"),
            ],
        )


def test_memory_bundle_roundtrip_and_delegated_request() -> None:
    bundle = MemoryBundle(items=[{"probe": "p1"}], metadata={"env": "test"})
    restored = MemoryBundle.from_json(bundle.to_json())
    assert restored.items == [{"probe": "p1"}]
    assert restored.metadata["env"] == "test"

    req = DelegatedMemoryReadRequest(
        namespaces=(MemoryNamespace(project_id="cortensor-route-bench"),),
        record_types=("diagnostic",),
    )
    assert req.max_results == 50


def test_agent_rejects_mixed_runtime_and_config_path() -> None:
    with pytest.raises(ValueError, match="cannot be used together"):
        Agent(instructions="hi", runtime=object(), config_path="missing.yaml")  # type: ignore[arg-type]


def test_run_with_backoff_retries_transient_provider_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    from openminion import ProviderError

    monkeypatch.setattr("time.sleep", lambda *_: None)
    calls = {"count": 0}

    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise ProviderError("RATE_LIMITED: HTTP 429")
        return "ok"

    out, attempts = run_with_backoff(flaky, max_attempts=3, base_delay_seconds=0.01)
    assert out == "ok"
    assert attempts == 3


def test_parse_structured_reply_strips_openminion_prefix_and_fences() -> None:
    raw = 'openminion: ```json\n{"status": "ok", "sdk_version": "0.1.23", "finding": "Prefix handled"}\n```'
    parsed, meta = parse_structured_reply(raw, ProbeCheckOutput)
    assert parsed.status == "ok"
    assert parsed.sdk_version == "0.1.23"
    assert meta["had_agent_prefix"] is True
    assert meta["had_markdown_fence"] is True


def test_detect_runtime_interception_catches_policy_and_task_guards() -> None:
    assert detect_runtime_interception("openminion: Policy confirmation required.") == "POLICY_CONFIRMATION_REQUIRED"
    assert detect_runtime_interception("I could not safely update the task conditions.") == "INVALID_TASK_CONTEXT_UPDATE"
    assert detect_runtime_interception("openminion: Route benchmark ready.") is None
