# OpenMinion Building Blocks Tested

## Source Snapshot

- **Repository:** `https://github.com/openminion/openminion`
- **Version (`openminion.__version__`):** `0.1.24`
- **Commit:** `a52088443c67a47c8fbf660f47ec6f748b3247f3`
- **Python Runtime:** `3.13.18`

## 1. Decorated Read-Only Tools (`@tool`)

- Symbol: `openminion.tools.tool` (`src/openminion/tools/decorator.py:302`)
- Project usage: `triage.assess_issue` and `triage.assess_release` registered with `min_scope="READ_ONLY"` and `idempotent=True`.
- Verified behavior: Attaches `ToolDecl`, validates inputs against generated Pydantic models, and exposes `declaration.tool_family_spec()`. Direct handler invocation expects either a dict or the generated Pydantic model instance; routing via `ToolRegistry` provides consistent argument validation and structured wrapping.

## 2. Tool Derivation & Execution (`derive_tool_specs`, `ToolRegistry`, `ProviderToolCall`)

- Symbols:
  - `derive_tool_specs` (`openminion.modules.tool.framework.py:96`)
  - `ToolRegistry.execute_calls` (`openminion.modules.tool.registry/__init__.py:274`)
  - `ProviderToolCall` (`openminion.modules.tool.contracts/provider_types.py:16`)
  - `ToolExecutionContext` (`openminion.modules.tool.base.py:17`)
- Verified behavior: Every issue and release run dispatches a `ProviderToolCall` with trace/session context and receives `ok=True`, `verified=True`, duration metrics, and structured JSON in `result.content`.

## 3. SQLite Session Persistence (`SQLiteSessionStore`)

- Symbol: `SQLiteSessionStore` (`openminion.modules.session.storage/store.py:249`)
- Verified behavior:
  - Both in-memory (`:memory:`) and disk-backed (`.triage_demo/demo.db`) SQLite databases store sessions, `session_events`, and assistant turns across CLI invocations.
  - Note: Events are written to `session_events` (12 rows across 3 sessions), while `create_session()` writes an initial `agent.bound` bookkeeping event automatically.
  - Both `triage_issue` and `triage_release` persist the serialized `openminion-triage.v1` JSON report via `append_turn(..., "assistant", ...)` (`3` sessions and `3` saved turns verified in `.triage_demo/demo.db`).

## 4. Recursive Task State (`TaskState`)

- Symbol: `TaskState` (`openminion.modules.brain.loop.recursive.schemas.py:77`)
- Verified behavior: Encodes `plan_id`, `step_id`, `retry_count`, `verification_mode="rule_based"`, and strict invariants (`extra="allow"` preserved cleanly on serialization).

## 5. Lifecycle Phase Diagnostics (`PhaseStatus`, `coerce_phase_status`, `phase_status_payload`)

- Symbols: `PhaseStatus`, `coerce_phase_status`, `phase_status_payload` (`openminion.modules.brain.diagnostics/status.py:115, 160, 232`)
- Verified behavior: Issue runs emit `analyzing` -> `completed` and release runs emit `verifying` -> `completed`, each exposing language-neutral `facts` dictionaries in `diagnostics.phase_statuses`. `coerce_phase_status` safely accepts raw mapping inputs and defaults unknown status keys to `working`.

## Verification Matrix

1. **Offline Unit & Integration Suite:**
   - `.venv/bin/python -m pytest -q` -> **11 passed in 1.06s** (exit code `0`).
   - Uses mocked GitHub REST transport, `httpx.MockTransport` for OpenAI-compatible inference, real `openminion==0.1.24` registry/session/diagnostics modules, and file/memory SQLite verification.
2. **Live Model-Backed Runs (`openai/gpt-oss-120b` via OpenAI-compatible API):**
   - `samples/issue.json` (`example/project` #42): `high` severity, reproduction `100/100`, non-empty `model_notes` (`artifacts/live_issue_fixture.json`).
   - `openminion/openminion` issue `#236` (live GitHub REST fetch + live model): `medium` severity, reproduction `70/100`, non-empty `model_notes` identifying sandbox CI risk and missing logs (`artifacts/live_openminion_issue_236.json`).
   - `samples/release.json` (`v1.4.0`): `hold` verdict on unchecked `Migration notes reviewed`, persisted turn in SQLite (`artifacts/live_release_fixture.json`).
