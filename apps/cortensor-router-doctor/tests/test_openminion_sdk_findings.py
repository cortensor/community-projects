"""Minimal, reproducible offline test suite proving verified OpenMinion 0.1.24 SDK findings.

Each test targets an exact verified bug in `openminion==0.1.24` with file/line citations:
- BUG-1: Ollama default `tool_call_strategy='fallback'` omits `payload['tools']`, disables fallback
         parsing for normal tools, and has a missing `f`-string in `EMPTY_PAYLOAD`.
- BUG-2: `TurnHandle.stream(timeout_s=...)` and `subscribe(timeout_s=...)` ignore `Condition.wait()`
         timeout return values and loop forever (upstream issue #872).
- BUG-3: `MemoryMerger._import_direct_mode` performs non-atomic partial writes before returning
         `applied=False` when `conflict_mode='error'` hits a later conflict (upstream issue #873).
- BUG-4: `MemoryMerger.import_snapshot` silently ignores `options.namespace_allowlist`
         (upstream issue #873).
- BUG-5: `Handoff.resolved_description()` raises `IndexError` on whitespace-only target instructions.
- BUG-6: Parent and child `Agent` sharing a `@tool` callable collide in `ToolRegistry` during a
         handoff run (workaround: pass tool name strings to the child `subagent`).
"""

from __future__ import annotations

from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
import threading
import time
from typing import Any
from unittest.mock import patch

import pytest
from openminion import Agent, Handoff, subagent
from openminion.base.config.providers import OllamaProviderConfig
from openminion.modules.llm.errors import LLMCtlError
from openminion.modules.llm.providers.ollama.adapter import OllamaProvider
from openminion.modules.llm.schemas import LLMRequest, Message, ToolSpec
from openminion.modules.memory.models import MemoryNamespace
from openminion.modules.memory.portability.models import (
    MemoryBundleExportOptions,
    MemoryBundleImportOptions,
)
from openminion.modules.runtime.contracts import TurnResponse
from openminion.services.runtime.turn_handle import TurnHandle

from cortensor_router_doctor.agent import create_isolated_runtime
from cortensor_router_doctor.tools import probe_cortensor_router


def test_bug1_ollama_default_fallback_drops_tools_and_has_missing_fstring() -> None:
    """Verify OllamaProviderConfig defaults to 'fallback', dropping standard tool calls,
    and emits literal '{model}' on EMPTY_PAYLOAD.

    Source:
    - openminion/base/config/providers.py:85 (`tool_call_strategy: str = "fallback"`)
    - openminion/modules/llm/providers/ollama/adapter.py:244,269-270,323,332-333
    """
    assert OllamaProviderConfig().tool_call_strategy == "fallback"

    provider = OllamaProvider()
    req = LLMRequest(
        messages=[Message(role="user", content="Probe the Cortensor router")],
        tools=[
            ToolSpec(
                name="probe_cortensor_router",
                description="Probe router",
                input_schema={"type": "object", "properties": {"endpoint_url": {"type": "string"}}},
            )
        ],
    )
    captured_default: dict[str, Any] = {}

    def _mock_fallback_post(**kwargs: Any) -> dict[str, Any]:
        captured_default["payload"] = kwargs["payload"]
        return {
            "model": "qwen2.5:1.5b",
            "message": {
                "role": "assistant",
                "content": '{"tool": "probe_cortensor_router", "arguments": {"endpoint_url": "http://127.0.0.1:8080"}}',
            },
            "done_reason": "stop",
        }

    try:
        # Under default config (fallback): no `tools` sent AND fallback parser disabled for normal tools!
        with patch(
            "openminion.modules.llm.providers.ollama.adapter._http_json_post",
            side_effect=_mock_fallback_post,
        ):
            resp_default = provider.complete(req, config={"model": "qwen2.5:1.5b"})

        assert "tools" not in captured_default["payload"]
        assert resp_default.tool_calls == []

        # Under explicit tool_call_strategy="native": `tools` IS sent and native tool_calls ARE parsed!
        captured_native: dict[str, Any] = {}

        def _mock_native_post(**kwargs: Any) -> dict[str, Any]:
            captured_native["payload"] = kwargs["payload"]
            return {
                "model": "qwen2.5:1.5b",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "probe_cortensor_router",
                                "arguments": {"endpoint_url": "http://127.0.0.1:8080"},
                            }
                        }
                    ],
                },
                "done_reason": "stop",
            }

        with patch(
            "openminion.modules.llm.providers.ollama.adapter._http_json_post",
            side_effect=_mock_native_post,
        ):
            resp_native = provider.complete(
                req,
                config={"model": "qwen2.5:1.5b", "tool_call_strategy": "native"},
            )

        assert "tools" in captured_native["payload"]
        assert len(resp_native.tool_calls) == 1
        assert resp_native.tool_calls[0].name == "probe_cortensor_router"

        # Missing `f` prefix at adapter.py:333 produces literal "{model}"
        with patch(
            "openminion.modules.llm.providers.ollama.adapter._http_json_post",
            return_value={
                "model": "qwen2.5:1.5b",
                "message": {"role": "assistant", "content": ""},
            },
        ):
            with pytest.raises(LLMCtlError) as exc_info:
                provider.complete(
                    LLMRequest(messages=[Message(role="user", content="hello")]),
                    config={"model": "qwen2.5:1.5b"},
                )
        assert exc_info.value.code == "EMPTY_PAYLOAD"
        assert "ollama pull {model}" in exc_info.value.message
    finally:
        provider.close()


def test_bug2_turn_handle_stream_ignores_timeout_s() -> None:
    """Verify `TurnHandle.stream(timeout_s=...)` hangs past timeout_s.

    Upstream issue: https://github.com/openminion/openminion/issues/872
    Source: openminion/services/runtime/turn_handle.py:242-261
    """
    handle = TurnHandle(trace_id="bug2-timeout-test", on_cancel=lambda _: True)
    finished = threading.Event()
    errors: list[BaseException] = []

    def _consume() -> None:
        try:
            next(handle.stream(timeout_s=0.05))
        except StopIteration:
            pass
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            finished.set()

    worker = threading.Thread(target=_consume, daemon=True)
    worker.start()

    # Wait 4x longer than timeout_s=0.05; stream() MUST still be blocked due to the infinite loop bug.
    time.sleep(0.20)
    still_blocked = not finished.is_set()

    # Cleanly unblock the worker thread so the test leaves no dangling threads.
    handle._set_result(TurnResponse(final_text="unblocked"))  # noqa: SLF001
    worker.join(timeout=2.0)

    assert still_blocked is True
    assert errors == []
    assert finished.is_set()


def test_bug3_memory_merger_non_atomic_partial_write_on_conflict_error(tmp_path: Path) -> None:
    """Verify `MemoryMerger._import_direct_mode` persists earlier records before hitting a
    later conflict under `conflict_mode='error'`, despite returning `applied=False`.

    Upstream issue: https://github.com/openminion/openminion/issues/873
    Source: openminion/modules/memory/portability/merger.py:341-417
    """
    rt_src = create_isolated_runtime(tmp_path / "src", provider="echo")
    rt_dst = create_isolated_runtime(tmp_path / "dst", provider="echo")
    try:
        svc_src = rt_src.runtime_memory_assembly.service
        svc_dst = rt_dst.runtime_memory_assembly.service

        id_1 = svc_src.write_record(
            scope="agent:router-doctor",
            record_type="fact",
            title="Non-conflicting record 1",
            content={"idx": 1, "status": "ok"},
        )
        id_2 = svc_src.write_record(
            scope="agent:router-doctor",
            record_type="fact",
            title="Conflicting record 2",
            content={"idx": 2, "status": "v1"},
        )
        snapshot = svc_src.export_bundle_snapshot(
            MemoryBundleExportOptions(scopes=["agent:router-doctor"], types=["fact"])
        )

        # Ensure record 1 precedes record 2 in snapshot order and seed conflicting record 2 in dst.
        ordered_records = [
            next(r for r in snapshot.records if r.id == id_1),
            next(r for r in snapshot.records if r.id == id_2),
        ]
        ordered_snapshot = replace(snapshot, records=ordered_records)
        svc_dst._store.put(  # noqa: SLF001
            replace(ordered_records[1], content={"idx": 2, "status": "v2_conflict"})
        )

        result = svc_dst.import_bundle_snapshot(
            ordered_snapshot,
            MemoryBundleImportOptions(
                trust_mode="direct",
                conflict_mode="error",
                id_mode="preserve",
            ),
        )
        # Bug: claims applied=False with conflicts, yet imported_records==1 and id_1 is persisted!
        assert result.applied is False
        assert len(result.conflicts) == 1
        assert result.imported_records == 1
        assert svc_dst._store.get(id_1) is not None  # noqa: SLF001
    finally:
        rt_src.close()
        rt_dst.close()


def test_bug4_memory_merger_ignores_namespace_allowlist(tmp_path: Path) -> None:
    """Verify `MemoryMerger` ignores `MemoryBundleImportOptions.namespace_allowlist`.

    Upstream issue: https://github.com/openminion/openminion/issues/873
    Source: openminion/modules/memory/portability/merger.py:73-125
    """
    rt_src = create_isolated_runtime(tmp_path / "src_ns", provider="echo")
    rt_dst = create_isolated_runtime(tmp_path / "dst_ns", provider="echo")
    try:
        svc_src = rt_src.runtime_memory_assembly.service
        svc_dst = rt_dst.runtime_memory_assembly.service

        rec_id = svc_src.write_record(
            scope="agent:untrusted-peer",
            record_type="fact",
            title="Untrusted peer record",
            content={"source": "untrusted"},
        )
        snapshot = svc_src.export_bundle_snapshot(
            MemoryBundleExportOptions(scopes=["agent:untrusted-peer"], types=["fact"])
        )

        # Explicitly restrict import to agent_id="router-doctor" ONLY:
        result = svc_dst.import_bundle_snapshot(
            snapshot,
            MemoryBundleImportOptions(
                trust_mode="direct",
                conflict_mode="skip",
                namespace_allowlist=[MemoryNamespace(agent_id="router-doctor")],
            ),
        )
        # Bug: MemoryMerger ignores namespace_allowlist and imports the disallowed record anyway.
        assert result.applied is True
        assert result.imported_records == 1
        assert svc_dst._store.get(rec_id) is not None  # noqa: SLF001
    finally:
        rt_src.close()
        rt_dst.close()


def test_bug5_handoff_resolved_description_crashes_on_whitespace_instructions() -> None:
    """Verify `Handoff.resolved_description()` raises `IndexError` on whitespace-only instructions.

    Source: openminion/api/handoff.py:154-159
    """
    blank_agent = Agent(name="whitespace-target", instructions="   \n\t  ")
    handoff = Handoff(target=blank_agent)
    with pytest.raises(IndexError):
        handoff.resolved_description()


def test_bug6_shared_decorated_tool_handoff_collision(tmp_path: Path) -> None:
    """Verify passing the same `@tool` callable to both parent and child `subagent` collides
    in `ToolRegistry` when the parent's run scope is active.

    Source: openminion/api/agent.py:196-238 (`_register_tools_for_run`)
    Workaround: pass the tool name string (`"probe_cortensor_router"`) to `subagent(...)`.
    """
    rt = create_isolated_runtime(tmp_path / "rt_collision", provider="echo")
    try:
        parent = Agent(
            name="parent-auditor",
            runtime=rt,
            instructions="Parent auditor",
            tools=[probe_cortensor_router],
        )
        # Anti-pattern: passing the decorated callable again to child causes registry collision
        child_broken = subagent(
            parent,
            name="child-broken",
            instructions="Child auditor",
            tools=[probe_cortensor_router],
        )
        # Workaround: passing the registered tool name string registers zero duplicate specs
        child_fixed = subagent(
            parent,
            name="child-fixed",
            instructions="Child auditor",
            tools=["probe_cortensor_router"],
        )

        with ExitStack() as parent_risk:
            p_tools, p_profiles = parent._register_tools_for_run(rt.tools, parent_risk)  # noqa: SLF001
            try:
                # Re-registering the same @tool callable in child raises ValueError / ToolRuntimeError
                with ExitStack() as child_risk:
                    with pytest.raises((ValueError, Exception)):
                        child_broken._register_tools_for_run(rt.tools, child_risk)  # noqa: SLF001

                # Fixed child succeeds cleanly with no duplicate registrations
                with ExitStack() as fixed_risk:
                    c_tools, c_profiles = child_fixed._register_tools_for_run(  # noqa: SLF001
                        rt.tools, fixed_risk
                    )
                    assert c_tools == []
                    assert c_profiles == []
                    assert "probe_cortensor_router" in child_fixed.tools
            finally:
                parent._unregister_tools(rt.tools, p_tools, p_profiles)  # noqa: SLF001
    finally:
        rt.close()
