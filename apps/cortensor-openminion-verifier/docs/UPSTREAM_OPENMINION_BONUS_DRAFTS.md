# Upstream OpenMinion Issue & Minimal Patch Drafts (Bonus Track)

> **Status**: Staged locally for **manual human filing** against [`openminion/openminion`](https://github.com/openminion/openminion) (targeting verified PyPI release `openminion==0.1.21`) for the **Hackathon #5 Bonus Track**.
> Do not auto-submit from CI or agent loops; review each repro and patch manually before opening upstream issues or PRs.
> All snippets below were verified directly against the installed `openminion==0.1.21` site-packages and scrubbed of credentials and private URLs.

## Filed Upstream Issues & Fix PRs (2026-11-16)

- **Draft 1 (`TurnResponse.telemetry` token totals)** — **Acknowledged & Confirmed in Scope by Maintainer (`@wireindevice`)**:
  - Upstream Issue: [`openminion/openminion#773`](https://github.com/openminion/openminion/issues/773)
  - Substantive Fix PR (targeting `dev`): [`openminion/openminion#775`](https://github.com/openminion/openminion/pull/775)
- **Draft 2 (`Handoff` target `timeout_seconds` & `approval_callback` forwarding)** — **Acknowledged & Confirmed in Scope by Maintainer (`@wireindevice`)**:
  - Upstream Issue + Concrete Design Proposal: [`openminion/openminion#774`](https://github.com/openminion/openminion/issues/774)

---

## Draft 1 — `TurnResponse.telemetry` Reports `tokens_in=0, tokens_out=0` While `TurnResponse.stats` Has Non-Zero Usage

- **Upstream Repo**: `openminion/openminion` (`0.1.21`)
- **Suggested Title**: `bug(runtime): TurnResponse.telemetry reports zero tokens even when TurnResponse.stats has token totals`
- **Source Location**: `openminion/services/runtime/daemon.py:549-555` (inspected in `_turn_success_response()`, lines `527-558`)

### Problem Summary

In `openminion==0.1.21`, `_turn_success_response()` builds `TurnResponse.stats` from `turn_result.stats.as_payload()` (`RunStats` in `openminion/modules/telemetry/usage/types.py`, which exposes `input_tokens` and `output_tokens`), while post-execution accounting writes `total_input_tokens_used` and `total_output_tokens_used` into `turn_result.metadata` (`openminion/services/brain/post_execution/usage.py` / `postprocess_metadata.py`). Meanwhile `TurnResponse.telemetry` reads `metadata.get("usage_prompt_tokens")` and `metadata.get("usage_completion_tokens")` (`openminion/services/runtime/daemon.py:549-555`), so `TurnResponse.stats` reports real token counts while `TurnResponse.telemetry.tokens_in` and `TurnResponse.telemetry.tokens_out` both silently report `0`.

### Minimal Reproduction

```python
from pathlib import Path
from openminion.api.runtime import APIRuntime
from openminion.base.config import OpenMinionConfig  # configure provider/model as usual

runtime = APIRuntime.from_config(
    config=OpenMinionConfig(),
    home_root=Path("./tmp-home"),
    data_root=Path("./tmp-data"),
)
resp = runtime.submit_turn(
    payload={"session_id": "repro", "message": "Reply with OK.", "stream": True}
).result()
print("stats:", resp.stats)
print("telemetry:", resp.telemetry)
# Actual: stats has non-zero input_tokens / output_tokens,
#         while telemetry.tokens_in == 0 and telemetry.tokens_out == 0.
```

### Expected vs. Actual

- **Expected**: `TurnResponse.telemetry.tokens_in` and `TurnResponse.telemetry.tokens_out` reflect `turn_result.stats` / post-execution token metadata when `usage_prompt_tokens` / `usage_completion_tokens` are absent from `metadata`.
- **Actual**: `TurnResponse.telemetry.tokens_in == 0` and `TurnResponse.telemetry.tokens_out == 0` across calibrated runs where `TurnResponse.stats` reports real token usage.

### Minimal Patch Draft

```diff
--- a/openminion/services/runtime/daemon.py
+++ b/openminion/services/runtime/daemon.py
@@ -537,19 +537,28 @@ def _turn_success_response(
         session_id=request.session_id,
         trace_id=request.trace_id,
     )
+    stats_payload = (
+        turn_result.stats.as_payload()
+        if turn_result.stats is not None and turn_result.stats.has_any_data
+        else {}
+    )
+    tokens_in = (
+        _to_int(metadata.get("usage_prompt_tokens"))
+        or _to_int(stats_payload.get("input_tokens"))
+        or _to_int(metadata.get("total_input_tokens_used"))
+    )
+    tokens_out = (
+        _to_int(metadata.get("usage_completion_tokens"))
+        or _to_int(stats_payload.get("output_tokens"))
+        or _to_int(metadata.get("total_output_tokens_used"))
+    )
     return TurnResponse(
         final_text=turn_result.body,
         metadata=metadata,
-        stats=turn_result.stats.as_payload()
-        if turn_result.stats is not None and turn_result.stats.has_any_data
-        else {},
+        stats=stats_payload,
         artifacts=artifact_refs,
         tool_calls_summary=tool_calls,
         memory_write_intents=[],
         telemetry=TurnTelemetry(
-            tokens_in=_to_int(metadata.get("usage_prompt_tokens")),
-            tokens_out=_to_int(metadata.get("usage_completion_tokens")),
+            tokens_in=tokens_in,
+            tokens_out=tokens_out,
             duration_ms=duration_ms,
             retries=0,
             queue_wait_ms=0,
```

---

## Draft 2 — `build_delegate_tool(Handoff)` Drops `timeout_seconds` and `approval_callback` When Calling `handoff.target.run()`

- **Upstream Repo**: `openminion/openminion` (`0.1.21`)
- **Suggested Title**: `bug(handoff): allow Handoff delegate tools to forward timeout_seconds and approval_callback to handoff.target.run()`
- **Source Location**: `openminion/api/handoff.py:168-170` (inspected alongside `Handoff`, lines `140-198`)

### Problem Summary

`build_delegate_tool()` compiles each `Handoff` into `transfer_to_<name>`, where `_handler_fn(message: str)` calls `handoff.target.run(message)` with no keyword arguments (`openminion/api/handoff.py:168-170`), and `_handler(arguments, _runtime_ctx=None)` discards `_runtime_ctx` (line `185`). As a result, delegated targets always fall back to the default `90.0`s `timeout_seconds` and `approval_callback=None` instead of respecting per-handoff or caller-configured timeout/approval controls.

### Minimal Reproduction

```python
from openminion import Agent, Handoff
from openminion.api.runtime import APIRuntime

runtime = APIRuntime.from_config(...)  # configured APIRuntime
specialist = Agent(runtime=runtime, name="specialist")
coordinator = Agent(
    runtime=runtime,
    handoffs=[Handoff(target=specialist, name="specialist")],
)
# Outer coordinator timeout_seconds / approval_callback cannot reach specialist.run(message)
# because Handoff has no timeout/approval fields and build_delegate_tool calls target.run(message).
result = coordinator.run("Delegate a brief check.", timeout_seconds=180.0)
```

### Expected vs. Actual

- **Expected**: `Handoff` accepts optional `timeout_seconds` and `approval_callback` (and forwards them when configured in `build_delegate_tool`), so slow upstream endpoints or dangerous delegated tools inherit explicit execution/approval boundaries.
- **Actual**: `handoff.target.run(message)` runs with default `90.0`s timeout and `approval_callback=None`.

### Minimal Patch Draft

```diff
--- a/openminion/api/handoff.py
+++ b/openminion/api/handoff.py
@@ -143,6 +143,8 @@ class Handoff:
     target: "Agent[Any, Any]"
     name: str | None = None
     description: str | None = None
+    timeout_seconds: float | None = None
+    approval_callback: Any | None = None
 
     def resolved_name(self) -> str:
         """Return the sanitized handoff tool name."""
@@ -166,7 +168,12 @@ def build_delegate_tool(handoff: Handoff) -> ToolDecl:
     description = handoff.resolved_description()
 
     def _handler_fn(message: str) -> dict[str, Any]:
-        result = handoff.target.run(message)
+        run_kwargs: dict[str, Any] = {}
+        if handoff.timeout_seconds is not None:
+            run_kwargs["timeout_seconds"] = handoff.timeout_seconds
+        if handoff.approval_callback is not None:
+            run_kwargs["approval_callback"] = handoff.approval_callback
+        result = handoff.target.run(message, **run_kwargs)
         return {
             "handoff": name,
             "target": getattr(handoff.target, "name", name),
```

---

## Draft 3 — `resolve_entry_task_update()` Raises `ValueError` Across Sequential `subagent()` Turns and Duplicate Parallel Entry `task_update` Payloads

- **Upstream Repo**: `openminion/openminion` (`0.1.21`)
- **Suggested Title**: `bug(brain): avoid false clarify detours in resolve_entry_task_update() when task_update is omitted on non-clarify turns or duplicated across parallel entry tool calls`
- **Source Location**: `openminion/modules/brain/loop/context/task_context.py:173-191`

### Problem Summary

In `resolve_entry_task_update()` (`openminion/modules/brain/loop/context/task_context.py:173-191`), two brittle checks cause `apply_entry_task_context()` to catch `ValueError` and divert turns into `clarify` (`reason_code="invalid_task_context_update"`):
1. Lines `173-181`: whenever `state.resolved_task_context` is already populated, omitting `task_update` raises `ValueError("Missing task_update for a clarification or active request")` even when `clarify=False` and `task_context_needs_update=False` (observed across sequential `subagent()` calls sharing/inheriting session state).
2. Lines `190-191`: when an LLM emits parallel entry tool calls carrying identical `task_update` sidecars, `len(patches) != 1` raises `ValueError("Exactly one task_update is allowed per entry response")`.

### Minimal Reproduction

```python
from types import SimpleNamespace
from openminion.modules.brain.loop.context.task_context import resolve_entry_task_update
from openminion.modules.brain.schemas.task_context import ResolvedTaskContext

active = ResolvedTaskContext(
    revision=1,
    objective="Check node health",
    objective_kind="verbatim",
    sources={"$objective": "abc"},
    consumed_input="abc",
)
state = SimpleNamespace(resolved_task_context=active, task_context_needs_update=False)

# Case A: second sequential subagent/tool call omits optional task_update when clarify=False
resp_no_patch = SimpleNamespace(
    tool_calls=[SimpleNamespace(arguments={"query": "status"})]
)
# Raises ValueError("Missing task_update for a clarification or active request") at lines 173-181.
resolve_entry_task_update(state, resp_no_patch, user_input="Run second check", clarify=False)

# Case B: parallel entry tool calls repeat identical task_update dicts
patch = {"operation": "replace", "objective": "Run both checks"}
resp_parallel = SimpleNamespace(
    tool_calls=[
        SimpleNamespace(arguments={"query": "a", "task_update": dict(patch)}),
        SimpleNamespace(arguments={"query": "b", "task_update": dict(patch)}),
    ]
)
# Raises ValueError("Exactly one task_update is allowed per entry response") at lines 190-191.
resolve_entry_task_update(state, resp_parallel, user_input="Run both checks", clarify=False)
```

### Expected vs. Actual

- **Expected**: Non-clarification continuations with an active context preserve/advance `ResolvedTaskContext` cleanly when `task_update` is omitted, and parallel entry tool calls sharing identical `task_update` payloads collapse to the single patch instead of triggering a `clarify` failure.
- **Actual**: Both patterns raise `ValueError` and force `reason_code="invalid_task_context_update"`.

### Minimal Patch Draft

```diff
--- a/openminion/modules/brain/loop/context/task_context.py
+++ b/openminion/modules/brain/loop/context/task_context.py
@@ -171,24 +171,37 @@ def resolve_entry_task_update(
             raise ValueError("Autonomous continuation cannot rewrite user task context")
         return active
     if not patches:
-        if (
-            active is not None
-            or clarify
-            or getattr(state, "task_context_needs_update", False)
-        ):
+        if clarify or getattr(state, "task_context_needs_update", False):
             raise ValueError(
                 "Missing task_update for a clarification or active request"
             )
         digest = input_digest(str(user_input))
+        if active is not None and active.consumed_input == digest:
+            return active
+        revision = (active.revision + 1) if active is not None else 1
         return ResolvedTaskContext(
-            revision=1,
+            revision=revision,
             objective=str(user_input),
             objective_kind="verbatim",
             sources={"$objective": digest},
             consumed_input=digest,
         )
-    if len(patches) != 1:
+    unique_patches: list[Any] = []
+    seen_patches: set[str] = set()
+    for patch in patches:
+        try:
+            key = json.dumps(patch, sort_keys=True, ensure_ascii=True)
+        except TypeError:
+            unique_patches.append(patch)
+            continue
+        if key not in seen_patches:
+            seen_patches.add(key)
+            unique_patches.append(patch)
+    if len(unique_patches) != 1:
         raise ValueError("Exactly one task_update is allowed per entry response")
-    raw_patch = patches[0]
+    patches = unique_patches
+    raw_patch = patches[0]
```
