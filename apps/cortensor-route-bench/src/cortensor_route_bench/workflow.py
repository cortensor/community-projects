"""Multi-agent PoI-style route consistency and architecture verification workflow."""

from __future__ import annotations

import json
import time
from typing import Any, TypeVar

from openminion import Agent, APIRuntime, Handoff, subagent
from openminion.api.handoff import DelegatedMemoryReadRequest
from pydantic import BaseModel
from sophiagraph.models import MemoryNamespace

from .config import redact_secrets
from .models import (
    ConsensusVerdict,
    WorkerEvaluation,
    detect_runtime_interception,
    parse_structured_reply,
)
from .probes import json_schema_instruction, run_with_backoff
from .tools import (
    capture_validated_contracts,
    check_endpoint_health,
    evaluate_json_contract,
    inspect_openminion_runtime_snapshot,
    inspect_provider_profile,
)

ModelT = TypeVar("ModelT", bound=BaseModel)


def _run_structured_agent(
    agent: Agent[Any, Any],
    prompt: str,
    model_cls: type[ModelT],
    *,
    runtime: APIRuntime | None = None,
    model: str | None = None,
    max_repair_turns: int = 2,
) -> tuple[ModelT, dict[str, object]]:
    """Run an OpenMinion agent, enforce guard checks, and validate structured reply or tool contract."""
    started = time.perf_counter()
    with capture_validated_contracts() as captured:
        res, attempts = run_with_backoff(lambda: agent.run(prompt))
        primary_run_id = res.run_id
        primary_run_state = res.run_state
        meta: dict[str, bool] = {}
        last_error: Exception | None = None
        best_grounded_text = ""

        for turn in range(max_repair_turns + 1):
            interception = detect_runtime_interception(res.text)
            if interception == "POLICY_CONFIRMATION_REQUIRED":
                raise RuntimeError(f"OpenMinion blocked execution with {interception}: {res.text[:240]}")
            if interception is None:
                best_grounded_text = res.text
                try:
                    parsed, meta = parse_structured_reply(res.text, model_cls)
                    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
                    return parsed, {
                        "run_id": primary_run_id,
                        "run_state": primary_run_state,
                        "elapsed_ms": elapsed_ms,
                        "attempts": attempts + turn,
                        "repaired_from_prose": turn > 0,
                        "payload_source": "final_text",
                        **meta,
                    }
                except Exception as exc:  # noqa: BLE001
                    matching = [payload for schema, payload in captured if schema == model_cls.__name__]
                    if matching:
                        parsed = model_cls.model_validate(matching[-1])
                        elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
                        return parsed, {
                            "run_id": primary_run_id,
                            "run_state": primary_run_state,
                            "elapsed_ms": elapsed_ms,
                            "attempts": attempts + turn,
                            "repaired_from_prose": turn > 0,
                            "payload_source": "evaluate_json_contract_tool",
                            "had_agent_prefix": False,
                            "had_markdown_fence": False,
                        }
                    last_error = exc
            else:
                last_error = RuntimeError(f"Runtime guard triggered: {interception}")

            if turn < max_repair_turns:
                error_hint = redact_secrets(str(last_error))[:360]
                if best_grounded_text and runtime is not None and model is not None:
                    formatter = Agent(
                        name=f"{agent.name}_json",
                        instructions=json_schema_instruction(
                            model_cls,
                            (
                                f"Call evaluate_json_contract(raw_text=..., schema_name='{model_cls.__name__}') "
                                "to verify your JSON payload against the schema, then reply with ONLY that JSON object."
                            ),
                        ),
                        runtime=runtime,
                        model=model,
                        tools=[evaluate_json_contract],
                        forced_tools=["evaluate_json_contract"],
                    )
                    repair_prompt = (
                        f"Call evaluate_json_contract(schema_name='{model_cls.__name__}') to fix validation error "
                        f"({error_hint}) using these grounded findings:\n{best_grounded_text}"
                    )
                    res, extra_attempts = run_with_backoff(lambda: formatter.run(repair_prompt))
                else:
                    repair_prompt = (
                        f"{prompt} "
                        f"Fix validation error ({error_hint}) and output ONLY valid JSON with ALL required keys."
                    )
                    res, extra_attempts = run_with_backoff(lambda: agent.run(repair_prompt))
                attempts += extra_attempts

    raise RuntimeError(
        f"Failed to parse {model_cls.__name__} after {max_repair_turns + 1} turn(s): {last_error}"
    )


def _run_worker(
    parent: Agent[Any, Any],
    *,
    runtime: APIRuntime,
    name: str,
    role_prompt: str,
    task_prompt: str,
    model: str,
    tools: list[Any],
    forced_tools: list[str] | None = None,
    use_memory_scope: bool = False,
) -> tuple[WorkerEvaluation, dict[str, object]]:
    """Run one isolated subagent worker and return structured evaluation plus telemetry."""
    mem_req = (
        DelegatedMemoryReadRequest(
            namespaces=(MemoryNamespace(project_id="cortensor-route-bench"),),
            record_types=("diagnostic", "route"),
            max_results=10,
            max_context_tokens=1536,
        )
        if use_memory_scope
        else None
    )
    child = subagent(
        parent,
        name=name,
        instructions=json_schema_instruction(WorkerEvaluation, role_prompt),
        model=model,
        tools=tools,
        timeout_seconds=180,
        memory=mem_req,
    )
    if forced_tools:
        child.forced_tools = list(forced_tools)
    parsed, tele = _run_structured_agent(
        child,
        task_prompt,
        WorkerEvaluation,
        runtime=runtime,
        model=model,
    )
    return parsed, {"worker": name, **tele}


def run_consensus_benchmark(
    *,
    config_path: str,
    provider: str,
    model: str,
    task: str,
    pace_seconds: float = 1.5,
) -> tuple[ConsensusVerdict, dict[str, object]]:
    """Execute independent Analyst + Verifier subagents and synthesize via Coordinator Handoff."""
    runtime = APIRuntime.from_config_path(config_path, logging_mode="interactive")
    started = time.perf_counter()
    try:
        coordinator_seed = Agent(
            name="route_bench_coordinator",
            instructions="Coordinate independent Cortensor route verification workers.",
            runtime=runtime,
            model=model,
        )

        # Worker A: Runtime & Provider Transport Analyst
        eval_a, tele_a = _run_worker(
            coordinator_seed,
            runtime=runtime,
            name="transport_analyst",
            role_prompt=(
                "You are Worker A (Transport & SDK Analyst). Use inspect_provider_profile and "
                "inspect_openminion_runtime_snapshot to assess provider compatibility, tool calling support, "
                "and SDK configuration hygiene. Set worker_role='transport_analyst'. "
                'Example shape: {"worker_role":"transport_analyst","readiness":"READY","confidence":0.9,"key_findings":["..."],"risks":["..."],"recommended_action":"..."}'
            ),
            task_prompt=(
                f"Evaluate target provider='{provider}', model='{model}' for task: {task}. "
                "Call inspect_provider_profile and inspect_openminion_runtime_snapshot first, then output WorkerEvaluation JSON including recommended_action."
            ),
            model=model,
            tools=[inspect_provider_profile, inspect_openminion_runtime_snapshot, evaluate_json_contract],
            forced_tools=["inspect_provider_profile"],
            use_memory_scope=True,
        )

        time.sleep(pace_seconds)

        # Worker B: Independent Reliability & Risk Verifier
        eval_b, tele_b = _run_worker(
            coordinator_seed,
            runtime=runtime,
            name="reliability_verifier",
            role_prompt=(
                "You are Worker B (Reliability & Security Verifier). Independently review rate-limit resilience, "
                "Cortensor Portal non-tool-calling fallback needs, secret redaction, and reproducibility. "
                "Set worker_role='reliability_verifier'. "
                'Example shape: {"worker_role":"reliability_verifier","readiness":"WARN","confidence":0.88,"key_findings":["..."],"risks":["..."],"recommended_action":"..."}'
            ),
            task_prompt=(
                f"Independently audit reliability & safety for provider='{provider}', model='{model}' on task: {task}. "
                "Call inspect_provider_profile and check_endpoint_health on 'https://api.cortensor.app/health' if helpful, then output WorkerEvaluation JSON including recommended_action."
            ),
            model=model,
            tools=[check_endpoint_health, inspect_provider_profile, evaluate_json_contract],
            forced_tools=["inspect_provider_profile"],
            use_memory_scope=False,
        )

        time.sleep(pace_seconds)

        # Coordinator Synthesis via Handoff peer
        synthesizer_peer = Agent(
            name="consensus_synthesizer",
            instructions=json_schema_instruction(
                ConsensusVerdict,
                "You are the PoI-style Consensus Synthesizer. Compare Worker A and Worker B evaluations objectively, "
                "compute an agreement_score (0.0 to 1.0), highlight discrepancies, and produce a final ConsensusVerdict. "
                'Example shape: {"task":"...","decision":"READY","agreement_score":0.9,"worker_summaries":["..."],"discrepancies":[],"recommendations":["..."],"final_summary":"..."}',
            ),
            runtime=runtime,
            model=model,
        )
        coordinator = Agent(
            name="consensus_coordinator",
            instructions=json_schema_instruction(
                ConsensusVerdict,
                "Delegate synthesis to transfer_to_consensus_synthesizer and return the exact ConsensusVerdict JSON.",
            ),
            runtime=runtime,
            model=model,
            handoffs=[
                Handoff(
                    target=synthesizer_peer,
                    name="transfer_to_consensus_synthesizer",
                    description="Synthesize independent worker evaluations into one ConsensusVerdict.",
                )
            ],
            forced_tools=["transfer_to_consensus_synthesizer"],
        )

        synthesis_prompt = (
            f"Original Task: {task}\n\n"
            f"Worker A ({eval_a.worker_role}):\n{json.dumps(eval_a.model_dump(mode='json'), indent=2)}\n\n"
            f"Worker B ({eval_b.worker_role}):\n{json.dumps(eval_b.model_dump(mode='json'), indent=2)}\n\n"
            "Call transfer_to_consensus_synthesizer to produce the final ConsensusVerdict JSON."
        )
        verdict, coord_tele = _run_structured_agent(
            coordinator,
            synthesis_prompt,
            ConsensusVerdict,
            runtime=runtime,
            model=model,
        )
        total_ms = round((time.perf_counter() - started) * 1000.0, 2)

        telemetry = {
            "bench_model": model,
            "total_elapsed_ms": total_ms,
            "workers": [tele_a, tele_b],
            "worker_outputs": {
                eval_a.worker_role: eval_a.model_dump(mode="json"),
                eval_b.worker_role: eval_b.model_dump(mode="json"),
            },
            "coordinator": coord_tele,
        }
        return verdict, telemetry
    finally:
        runtime.close()
