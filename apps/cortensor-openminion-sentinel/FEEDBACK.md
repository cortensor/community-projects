# OpenMinion 0.1.23 Engineering Feedback — `cortensor-openminion-sentinel`

## Overview

During development of **Cortensor OpenMinion Sentinel** (`v0.1.0`) for **Cortensor Hackathon #5**, we built an automated 8-probe verification suite (`sentinel/probes.py`) and a multi-agent governance verification pipeline (`sentinel/engine.py`) targeting **`openminion==0.1.23`** on Python 3.12.

---

## Building Blocks Tested

Every building block below is continuously verified by `python -m sentinel.cli --probes-only` and `python -m unittest discover -s tests -v` (`8/8` probes passing in `10800.13 ms`):

| Probe ID | OpenMinion 0.1 Building Block | Verified Result (`openminion==0.1.23`) | Latency (ms) |
| :--- | :--- | :--- | ---: |
| `P1_runtime_bootstrap` | `APIRuntime.from_config()`, `runtime_posture()`, `capability_report()`, `tool_inventory_report()` | `PASS` — `agent=sentinel, mode=brain, brain_bridge=True, tools_indexed=104, cap_keys=7` | `35.26` |
| `P2_agent_tool_call` | `@tool(min_scope="READ_ONLY")` + `Agent.run()` full turn | `PASS` — `run_state=completed`, structured tool envelope returned and synthesized | `2301.94` |
| `P3_channel_authenticity` | `AgentProfileConfig(default_channel="console")` + `ChannelAuthenticityConfig(mode="warn")` | `PASS` — `default_channel=console, auth_mode=warn` accepted by `GatewaySecurity` | `0.01` |
| `P4_subagent_lineage` | `subagent(parent, name="skeptic", memory_posture="none")` | `PASS` — isolated child run context (`parent_transcript_inherited=False`, `trace_parent=agent:sentinel`) | `1281.01` |
| `P5_subagent_memory_guard` | `subagent(..., memory_posture="read_only_bounded")` v1 boundary | `PASS` — confirms expected `ValueError: developer subagent memory grants are not bound in v1` | `0.04` |
| `P6_handoff_delegation` | `Handoff(target=...)` + `build_delegate_tool()` | `PASS` — compiled `transfer_to_incident_desk` tool and completed delegated turn | `1502.52` |
| `P7_memory_bundle_v1` | `MemoryBundle(version="memory_bundle.v1")` `.to_json()` / `.from_json()` | `PASS` — deterministic JSON round-trip preserving schema version, items, and metadata | `0.09` |
| `P8_cortensor_provider` | `CortensorProviderConfig` (`/api/v2/completions`, `session_id=1`, `session_pool="auto"`) | `PASS` — executed full turn through `CortensorProvider` against `/api/v2/completions` | `2680.98` |

---

## What We Learned

### 1. `Agent(agent_id=..., name=...)` Profile Lookup Precedence
- **Observed Behavior:** When constructing `Agent(runtime=rt, agent_id="sentinel", name="Sentinel")`, the internal profile resolver uses `name` if provided to look up the key in `OpenMinionConfig.agents`. If `name` differs in casing from the dictionary key (`"Sentinel"` vs `"sentinel"`), `UnknownProfileError` is raised.
- **Recommendation:** Keep `AgentProfileConfig.name`, the dictionary key in `OpenMinionConfig.agents`, `agent_id`, and `Agent(name=...)` identical (e.g. `"sentinel"`), or allow `Agent` to use `agent_id` for config resolution while keeping `name` as a human-readable display label.

### 2. `AgentProfileConfig.default_channel` Defaults to `""` and Triggers `invalid_channel`
- **Observed Behavior:** By default, `AgentProfileConfig.default_channel` is `""`. When invoking `Agent.run()` programmatically via the Python SDK without specifying an explicit channel, `GatewaySecurity.evaluate_inbound_authenticity()` checks `if not channel:` before checking `policy.mode`, raising `RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)`.
- **Workaround Used in Sentinel:** Explicitly set `default_channel="console"` on every `AgentProfileConfig` alongside `enabled_channels=["console"]` and `ChannelAuthenticityConfig(mode="warn", trusted_channels=["console"])`.
- **Recommendation:** Default `AgentProfileConfig.default_channel` to `"console"` for programmatic SDK invocations when `"console"` is in `enabled_channels`.

### 3. `subagent()` `memory_posture="read_only_bounded"` Guard in v1
- **Observed Behavior:** Although `SubagentRunContext` documents `memory_posture in {"none", "read_only_bounded"}`, calling `subagent(parent, memory_posture="read_only_bounded")` directly raises `ValueError("developer subagent memory grants are not bound in v1")` in `openminion/api/handoff.py:293` (bounded grants are materialized internally when `memory=DelegatedMemoryReadRequest(...)` is supplied).
- **Workaround Used in Sentinel:** Use `memory_posture="none"` on child subagents and pass structured audit snapshots explicitly via `MemoryBundle(version="memory_bundle.v1")`.

### 4. Native `CortensorProviderConfig` Transport (`cortensor_completion` vs `openai_chat`)
- **Observed Behavior:** `CortensorProvider._resolve_api_mode()` selects `"cortensor_completion"` automatically when `base_url` ends with `/completions` (default `http://127.0.0.1:8080/api/v2/completions`) and supports hybrid tool-calling and response extraction from `choices[0].message.content` or `choices[0].text`.
- **What Worked Well:** Having first-class `CortensorProviderConfig` parameters (`session_id`, `session_pool="auto"`, `precommit_timeout_seconds`, `privacy_level="high"`, `tool_call_strategy="hybrid"`) built directly into `openminion.base.config.providers` made switching between Cortensor Router `/api/v2/completions` and OpenAI-compatible `/v1` endpoints seamless.

### 5. Windows SQLite Teardown File Locks (`brain/brain.db`)
- **Observed Behavior:** On Windows Python 3.12, tearing down a `TemporaryDirectory` immediately after `Agent.run()` can hit `PermissionError: [WinError 32]` on `brain/brain.db` if runtime components are still holding SQLite handles.
- **Workaround Used in Sentinel:** Always call `runtime.close()` inside a `finally:` block and construct temporary directories with `TemporaryDirectory(ignore_cleanup_errors=True)`.
