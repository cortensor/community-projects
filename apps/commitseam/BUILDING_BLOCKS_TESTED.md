# Building Blocks Tested (`openminion==0.1.24`)

All observations below were verified first-hand against pinned **`openminion==0.1.24`** on Python `3.12.16` in both offline deterministic loopback runs (`pytest -v`) and live Groq runs (`openai/gpt-oss-20b`, recorded in [`docs/live-sdk-receipts.json`](./docs/live-sdk-receipts.json)).

> **Fault Attribution Boundary**: CommitSeam deliberately injects two application-level crashes (`pre-commit` and `post-commit` inside `QueueLedger.enqueue`) to demonstrate recovery invariants. Every finding below distinguishes **genuine `openminion==0.1.24` SDK behavior** from **harness-injected faults**.

## Component Matrix

| OpenMinion 0.1.24 Building Block | How CommitSeam Uses It | Observed Status | Key Finding (Verified First-Hand) |
| --- | --- | --- | --- |
| `APIRuntime.from_config(...)` | Programmatic runtime bootstrap with isolated `om_home` / `om_data` / `openminion.sqlite` | Works with caveats | Requires keyword-only `config`, `home_root: Path`, `data_root: Path` (no defaults for `home_root`/`data_root`). Auto-registers 40+ built-in tool families on startup. |
| `AgentProfileConfig` | Declares `coord` and `triage` agent profiles | Rough edge | `default_channel` defaults to `""`, causing `RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)` unless `default_channel="console"` is set (matches upstream `#864`). |
| `@tool(min_scope=..., dangerous=..., idempotent=...)` | Registers `inspect_failure` (`READ_ONLY`) and `enqueue_rerun` (`WRITE_SAFE`, `dangerous=True`, `idempotent=False`) | Rough edge | Only accepts `{"READ_ONLY", "WRITE_SAFE", "POWER_USER", "UI_AUTOMATION"}` (`registry_toolspec.py:462`). Invalid scope strings (e.g. `"WRITE"`) are NOT validated at decoration time and fail late at runtime with `KeyError`. |
| `Agent.run(approval_callback=decide)` | Binds human approval to `(request_id, item_id, queue_path)` under `ActionPolicyConfig(mode="confirm")` | Works (caveat with `output_type`) | Cleanly blocks tool execution when `decide(...)` returns `False` (`0` rows written, `tool_calls=0`). However, when `Agent(..., output_type=BaseModel)` is set, denial returns plain text `'coord: Confirmation denied. The action was not run.'` and crashes in `_coerce_output` with `AgentOutputValidationError`. |
| `Agent(..., output_type=BaseModel)` | Tested during SDK probing for typed structured turn outputs | Rough edge | `_build_payload` (`api/agent.py:158-194`) never injects `output_type.model_json_schema()` into system prompts or `response_format`. Replies are also prefixed with `f"{agent_id}: "`, forcing `_extract_json_object` fallback on every turn. |
| `Handoff` | Exposes read-only `triage_failure` peer to coordinator `Agent` | Security caveat | `api/handoff.py:162` calls `target.run(message)` without forwarding the parent `approval_callback` (upstream `#774`/`#776`). CommitSeam enforces strictly `READ_ONLY` tools on `Handoff` peers and keeps all write tools on the coordinator. |
| `session_id` + turn leases | Retry attempts open a fresh `session_id` (`-s1` → `-s2`) under the same business `request_id` | Design boundary | Gateway dedupe (`services/gateway/service.py:428-501`) and `RuntimeEngine` tool cache (`services/runtime/engine.py:250-268`) record completion only AFTER tool return; immediate retry on a crashed `session_id` risks `SESSION_TURN_BUSY` (`turn_leases.py:89-161`). |
| `cancel_event` | Aborts the OpenMinion turn immediately on injected seam faults | Works cleanly | Passing `threading.Event` as `cancel_event` and setting it inside the fault seam terminates the turn cleanly (`RuntimeError: Turn cancelled.`) without wasting a post-crash LLM synthesis call. |
| `GroqProviderConfig` | Live real-LLM execution (`openai/gpt-oss-20b`) | Rough edge | Default model `llama-3.3-70b-versatile` returns HTTP 404 on Groq. `tool_call_strategy="hybrid"` can complete with `tool_calls=0` even when `forced_tools` is set; `tool_call_strategy="native"` invokes tools and fires `approval_callback` reliably. |
| `ProviderError` (`RATE_LIMITED`) | Organic post-tool failure observed live on Groq (`8K` TPM free tier) | Validated thesis live | Because `openminion==0.1.24` issues multiple internal LLM calls per turn (`~2.4K–7.7K` tokens), Groq organically raised `ProviderError: RATE_LIMITED` *after* `enqueue_rerun` committed to SQLite and *before* `Agent.run` returned — proving CommitSeam's SQLite ledger is essential even without injected faults! |
| `MemoryBundle.to_json()` | One-way read-only redacted audit artifact per scenario | Works cleanly | Round-trips cleanly to JSON; CommitSeam wraps items/metadata with recursive key+value secret and host-path redaction and never uses `MemoryBundle` as recovery authority. |
| `APIRuntime.close()` | Called in `finally` block after every run | Caveat | `with Agent(runtime=...)` does NOT close caller-owned `APIRuntime` (`api/agent.py:425`). Callers must always close `runtime` explicitly in `finally`. |
| `context_traces` | Read-only inspection in `commitseam diagnose` | Observed gap | `APIRuntime` exposes no public `context_traces` query method (`list_context_traces` lives under internal modules). In our live 5-session run, `openminion.sqlite` recorded `52` total events across all `5` sessions (including `session.context.budget` and `memory.context.built`), yet `0` `context.manifest.created` events under default `APIRuntime.from_config`. |

## Reproducible Verification Commands

Every finding above can be reproduced directly in this repository (`0` external credentials required for commands 1–5):

```bash
# 1. Run full offline suite (18 tests + 500 Hypothesis P1..P5 cases + real OpenMinion 0.1.24 loopback)
.venv/bin/pytest -v

# 2. Reproduce @tool(min_scope="WRITE") passing decoration silently, then failing at runtime
.venv/bin/python -c '
import tempfile
from pathlib import Path
from openminion import APIRuntime, Agent, OpenMinionConfig, tool
from openminion.base.config.core import ActionPolicyConfig, AgentProfileConfig, StorageConfig
from openminion.base.config.providers import OpenAIProviderConfig, ProvidersConfig
from commitseam.minion_adapter import _OfflineLoopbackServer

@tool(min_scope="WRITE", dangerous=True)
def bad_scope(item_id: str) -> str:
    return item_id

srv = _OfflineLoopbackServer(); srv.start()
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    cfg = OpenMinionConfig(
        storage=StorageConfig(path=str(p / "om.sqlite")),
        providers=ProvidersConfig(openai=OpenAIProviderConfig(api_key="k", base_url=srv.base_url, model="m", tool_call_strategy="native")),
        action_policy=ActionPolicyConfig(mode="confirm", allow_read_only_without_prompt=True),
        agents={"coord": AgentProfileConfig(name="coord", provider="openai", default_channel="console")},
        default_agent="coord",
    )
    rt = APIRuntime.from_config(config=cfg, home_root=p / "h", data_root=p / "d")
    try:
        with Agent(runtime=rt, agent_id="coord", tools=[bad_scope], forced_tools=["bad_scope"]) as ag:
            res = ag.run("Call bad_scope item_id=x", session_id="s1", approval_callback=lambda *_: True)
            print("RUNTIME_REPLY:", res.text)
    except Exception as exc:
        print("RUNTIME_ERROR:", type(exc).__name__, exc)
    finally:
        rt.close(); srv.close()
'

# 3. Reproduce APIRuntime.from_config failing with invalid_channel when default_channel is omitted
.venv/bin/python -c '
import tempfile
from pathlib import Path
from openminion import APIRuntime, Agent, OpenMinionConfig
from openminion.base.config.core import AgentProfileConfig, StorageConfig
from openminion.base.config.providers import OpenAIProviderConfig, ProvidersConfig

with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    cfg = OpenMinionConfig(
        storage=StorageConfig(path=str(p / "om.sqlite")),
        providers=ProvidersConfig(openai=OpenAIProviderConfig(api_key="k", base_url="http://127.0.0.1:9/v1", model="m")),
        agents={"coord": AgentProfileConfig(name="coord", provider="openai")},
        default_agent="coord",
    )
    rt = APIRuntime.from_config(config=cfg, home_root=p / "h", data_root=p / "d")
    try:
        with Agent(runtime=rt, agent_id="coord") as ag:
            ag.run("hello", session_id="s1")
    except RuntimeError as exc:
        print("REPRODUCED:", exc)
    finally:
        rt.close()
'

# 4. Reproduce approval denial crashing Agent(..., output_type=BaseModel) with AgentOutputValidationError
.venv/bin/python -c '
import tempfile
from pathlib import Path
from pydantic import BaseModel
from openminion import APIRuntime, Agent, AgentOutputValidationError, OpenMinionConfig, tool
from openminion.base.config.core import ActionPolicyConfig, AgentProfileConfig, StorageConfig
from openminion.base.config.providers import OpenAIProviderConfig, ProvidersConfig
from commitseam.minion_adapter import _OfflineLoopbackServer

class Out(BaseModel):
    status: str

@tool(min_scope="WRITE_SAFE", dangerous=True)
def enqueue_rerun(item_id: str) -> str:
    return "{\"status\":\"ok\"}"

srv = _OfflineLoopbackServer(); srv.start()
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    cfg = OpenMinionConfig(
        storage=StorageConfig(path=str(p / "om.sqlite")),
        providers=ProvidersConfig(openai=OpenAIProviderConfig(api_key="k", base_url=srv.base_url, model="m", tool_call_strategy="native")),
        action_policy=ActionPolicyConfig(mode="confirm", allow_read_only_without_prompt=True),
        agents={"coord": AgentProfileConfig(name="coord", provider="openai", default_channel="console")},
        default_agent="coord",
    )
    rt = APIRuntime.from_config(config=cfg, home_root=p / "h", data_root=p / "d")
    try:
        with Agent(runtime=rt, agent_id="coord", tools=[enqueue_rerun], forced_tools=["enqueue_rerun"], output_type=Out) as ag:
            ag.run("Call enqueue_rerun item_id=x", session_id="s1", approval_callback=lambda *_: False)
    except AgentOutputValidationError as exc:
        print("REPRODUCED:", type(exc).__name__, str(exc)[:140])
    finally:
        rt.close(); srv.close()
'

# 5. Run full offline CLI demo + diagnose reconciliation (0 credentials required)
.venv/bin/commitseam demo --yes --provider offline --run-dir /tmp/cs-offline --request-id demo-1
.venv/bin/commitseam diagnose --run-dir /tmp/cs-offline --request-id demo-1-post --json

# 6. Run live Groq demo + diagnose (requires GROQ_API_KEY)
.venv/bin/commitseam demo --yes --provider groq --model openai/gpt-oss-20b --run-dir /tmp/cs-live --request-id live-1
.venv/bin/commitseam diagnose --run-dir /tmp/cs-live --json
```
