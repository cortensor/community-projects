# What We Learned: OpenMinion `0.1.24` SDK Field Report & Recommendations

Building **Cortensor Router Doctor** end-to-end on **`openminion==0.1.24`** gave us deep visibility into both the strengths of OpenMinion's runtime architecture (clean `@tool` risk metadata, `ActionPolicy` approval gates, SQLite durable memory, SHA-256 verified bundle codecs) and six concrete SDK bugs / sharp edges that directly affect production agent developers.

Two of the highest-impact runtime/data-integrity bugs have already been filed upstream on `openminion/openminion`:
- **Upstream Issue #872**: [https://github.com/openminion/openminion/issues/872](https://github.com/openminion/openminion/issues/872) — `TurnHandle.stream(timeout_s=...)` & `subscribe(timeout_s=...)` infinite wait loop
- **Upstream Issue #873**: [https://github.com/openminion/openminion/issues/873](https://github.com/openminion/openminion/issues/873) — `MemoryMerger._import_direct_mode` non-atomic partial writes on `conflict_mode="error"` + ignored `namespace_allowlist`

---

## Reproducible Bug Reports (Exact File Paths, Line Numbers, & Concrete Fixes)

### 1. [P0 / Data Integrity & Security] `MemoryMerger` Non-Atomic Partial Writes + Ignored `namespace_allowlist`
- **Upstream Issue**: [openminion/openminion#873](https://github.com/openminion/openminion/issues/873)
- **Files & Lines**:
  - `openminion/modules/memory/portability/merger.py:73-125` (`import_snapshot`)
  - `openminion/modules/memory/portability/merger.py:341-417` (`_import_direct_mode`)
  - `sophiagraph/portability/models.py:39-46` (`MemoryBundleImportOptions.namespace_allowlist`)
- **Expected Behavior**:
  1. When `conflict_mode="error"` detects a conflict on *any* record in a bundle, zero records are persisted and `applied=False` with `imported_records=0`.
  2. When `options.namespace_allowlist` is provided, records whose effective `MemoryNamespace` does not match the allowlist are rejected or filtered.
- **Actual Behavior**:
  1. `_import_direct_mode` loops over `snapshot.records` and immediately calls `self._service._store.put(record)` at line 393 for non-conflicting records. When a subsequent record conflicts (`options.conflict_mode == "error"`, lines 377–385), it appends to `conflicts` and later returns `MemoryBundleImportResult(applied=False, imported_records=1, conflicts=[...])` — **leaving earlier records permanently written to SQLite** despite reporting `applied=False`.
  2. `options.namespace_allowlist` is never referenced anywhere in `merger.py`, so untrusted cross-agent records are silently imported even when an explicit allowlist is passed.
- **Reproducer**: `tests/test_openminion_sdk_findings.py::test_bug3_memory_merger_non_atomic_partial_write_on_conflict_error` & `test_bug4_memory_merger_ignores_namespace_allowlist`
- **Concrete Fix**:
  - Run a two-phase validation pass before any `_store.put()` call: (a) enforce `options.namespace_allowlist` against each rewritten record's effective `MemoryNamespace`, and (b) check all records for `exact_id_conflict` and `normalized_key_conflict` upfront. If `conflicts` is non-empty under `conflict_mode="error"`, return immediately with `applied=False, imported_records=0` before opening the write phase (ideally inside a single SQLite transaction).

---

### 2. [P0 / Availability Hang] `TurnHandle.stream(timeout_s=...)` & `subscribe(timeout_s=...)` Never Time Out
- **Upstream Issue**: [openminion/openminion#872](https://github.com/openminion/openminion/issues/872)
- **File & Lines**: `openminion/services/runtime/turn_handle.py:242-261` (`_iter_chunks`)
- **Expected Behavior**: Calling `handle.stream(timeout_s=0.05)` or `handle.subscribe(timeout_s=0.05)` when no new chunks arrive within `timeout_s` should stop waiting (raise `TimeoutError` or return cleanly).
- **Actual Behavior**: Line 258 calls `self._stream_cv.wait(timeout=timeout_s)` and **discards the boolean return value** (`False` on timeout), immediately looping back into `while True:`. Callers specifying `timeout_s` hang indefinitely until `_result_ready` is set.
- **Reproducer**: `tests/test_openminion_sdk_findings.py::test_bug2_turn_handle_stream_ignores_timeout_s`
- **Concrete Fix**:
  ```python
  notified = self._stream_cv.wait(timeout=timeout_s)
  if not notified and timeout_s is not None:
      raise TimeoutError(f"turn stream timed out after {timeout_s}s trace_id={self.trace_id}")
  ```

---

### 3. [P0 / Local DX Blocker] Ollama Default `tool_call_strategy="fallback"` Drops All Standard Tool Calls (+ Unformatted Error String)
- **Files & Lines**:
  - `openminion/base/config/providers.py:85` (`OllamaProviderConfig.tool_call_strategy: str = "fallback"`)
  - `openminion/modules/llm/providers/ollama/adapter.py:244,269-270,323,332-333`
- **Expected Behavior**: An Ollama model supporting native tool calling (e.g. `qwen2.5:1.5b`, `llama3.1`) should work out of the box with `Agent(tools=[...])`, and `EMPTY_PAYLOAD` errors should interpolate the actual model name.
- **Actual Behavior**:
  1. Default `tool_call_strategy="fallback"` skips sending `payload["tools"]` (`adapter.py:269`), yet line 323 passes `fallback_enabled=bool(request.tools and schema_only_submit_output)`—which is `False` for all normal tools! Consequently, **neither native nor fallback tool calls work by default on Ollama**.
  2. Line 333 omits the `f` prefix: `"If using Ollama, ensure the model is pulled: 'ollama pull {model}'"` prints literal `{model}`.
- **Reproducer**: `tests/test_openminion_sdk_findings.py::test_bug1_ollama_default_fallback_drops_tools_and_has_missing_fstring`
- **Concrete Fix**:
  - Change `OllamaProviderConfig.tool_call_strategy` default to `"native"` (or `"hybrid"`), and at `adapter.py:323` set `fallback_enabled=bool(request.tools and (schema_only_submit_output or supports_fallback_tool_calling(tool_call_strategy)))`.
  - Add the missing `f` prefix at `adapter.py:333`.

---

### 4. [P1 / Multi-Agent Ergonomics] Shared `@tool` Callable Collision Between Parent `Agent` and `Handoff` Child `subagent`
- **File & Lines**: `openminion/api/agent.py:196-238` (`_register_tools_for_run`)
- **Expected Behavior**: Passing `tools=[probe_cortensor_router]` to both a parent `Agent` and a child created via `subagent(parent, tools=[probe_cortensor_router])` should execute cleanly when the parent delegates via `Handoff`.
- **Actual Behavior**: While the parent turn is active, `probe_cortensor_router` is registered in the shared `ToolRegistry`. When the child runs inside the `Handoff` handler, the child calls `registry.add(spec)` for the same tool name and collides with the already-registered spec.
- **Reproducer**: `tests/test_openminion_sdk_findings.py::test_bug6_shared_decorated_tool_handoff_collision`
- **Concrete Fix**: In `_register_tools_for_run`, if `registry.get(spec.name)` already holds an identical `ToolDecl` from an enclosing run scope (reference-counted or skipped from `registered`), reuse it without re-adding or unregistering it on child exit.

---

### 5. [P2 / Edge-Case Crash] `Handoff.resolved_description()` `IndexError` on Whitespace-Only Instructions
- **File & Lines**: `openminion/api/handoff.py:154-159`
- **Expected Behavior**: Fall back to `"Delegate this turn to the peer agent."` when `target.instructions` contains only whitespace.
- **Actual Behavior**: `bool("   ")` is `True`, so `str(instr).strip().splitlines()[0]` indexes an empty list and raises `IndexError: list index out of range`.
- **Reproducer**: `tests/test_openminion_sdk_findings.py::test_bug5_handoff_resolved_description_crashes_on_whitespace_instructions`
- **Concrete Fix**:
  ```python
  lines = str(instr).strip().splitlines()
  first_line = lines[0] if lines else ""
  ```

---

## Prioritized Product & SDK Recommendations for OpenMinion

1. **P0 — Auto-Inject `output_type` JSON Schema into `Agent` Prompts**: Currently `Agent(output_type=MyModel)` validates output post-hoc via `_coerce_output()`, leaving small/local models guessing exact field names unless the developer manually appends `MyModel.model_json_schema()` to `instructions`. Automatically appending a concise schema contract (or using native structured outputs when supported) would cut `AgentOutputValidationError` rates dramatically.
2. **P0 — Align `RuntimeConfig.chat_turn_timeout_seconds` with Provider Timeouts**: `CortensorProviderConfig` defaults to `timeout_seconds=420` and `precommit_timeout_seconds=300`, yet `RuntimeConfig.chat_turn_timeout_seconds` defaults to `90.0`s. When a profile selects `provider="cortensor"`, the runtime should either raise a config validation warning or auto-scale the turn timeout floor above the provider timeout.
3. **P1 — Make `AgentProfileConfig.default_channel` Default to `"console"`**: Programmatic SDK users calling `APIRuntime.from_config(...)` hit an obscure `invalid_channel` error when `default_channel` is left as `""` even though `OpenMinionConfig.enabled_channels` already defaults to `["console"]`.
4. **P1 — Ship an Opt-In `builtin_tools="none"` Mode on `APIRuntime`**: Exposing ~179 built-in tools by default bloats context and degrades tool-calling accuracy on smaller local/decentralized models (`1.5B–20B`). While passing explicit `tools=[...]` on `Agent` works as an allowlist, a runtime-level `builtin_tools="none"` flag would make lightweight, deterministic production agents faster to boot and easier to audit.
5. **P2 — First-Class Tool-Evidence Hooks for Anti-Hallucination Verification**: In safety-critical ops agents (like Cortensor Router quarantine), providing a built-in post-turn verifier hook `(run_result, tool_call_ledger) -> None` directly on `Agent` would standardize deterministic cross-checking between raw tool outputs and final LLM verdicts.
