# What We Learned — Actionable OpenMinion `0.1.24` & Cortensor Feedback

While building and stress-testing **`cortensor-prompt-shield`** on `openminion==0.1.24`, we ran directly into **5 concrete, reproducible rough edges/bugs** (all covered by automated tests in [`tests/test_prompt_shield.py`](./tests/test_prompt_shield.py)). Below are exact reproduction steps, expected vs. actual behavior, and targeted fixes that directly help Cortensor builders running local/edge models (Gemma4, 8B–20B miners, Portal).

---

## Finding 1 (High Impact for Cortensor Edge Models): 43.3 KB Default Outbound Request Bloat on Minimal SDK `Agent()` Calls

- **Observed:** Measuring the exact HTTP POST sent by `Agent(config_path=..., instructions="Reply OK.").run("hi")` against a local loopback OpenAI-compatible listener showed:
  - **Total HTTP body:** `43,301 bytes`
  - **System message alone:** `16,695 chars` (~4,170 tokens) of default `## Runtime Grounding`
  - **Built-in tools injected automatically:** `8` workspace tools even when the caller passed `tools=[]`!
- **Impact:** On prompt-budgeted / free-tier / small-context Cortensor miner models (e.g., 8 KB prompt-cap endpoints or 4K/8K context Gemma4/local models), the very first minimal SDK call fails with `HTTP 400: Total prompt content exceeds tier byte limit`.
- **Expected:** SDK callers instantiating `Agent(tools=[...], minimal_prompt=True)` (or `runtime.include_builtin_tools: false`) should be able to opt out of workspace grounding and built-in tools so a lean 2-tool agent stays under ~2 KB.
- **Our Workaround:** We built **`CompactGuardProxy`** (`src/cortensor_prompt_shield/guard_proxy.py`), which compacted live outbound payloads by **>85%** while preserving custom instructions, user messages, and `@tool` schemas verbatim.

---

## Finding 2 (Bug): `inbound authenticity` Raises Hard `RuntimeError` Even When `mode="warn"`

- **Upstream Issue:** https://github.com/openminion/openminion/issues/874
- **Repro:** Create a minimal `agents.json` where an agent entry omits `"default_channel": "console"`, leaving `channel_authenticity.mode` at its default `"warn"`, then call `agent.run("hi")`.
- **Actual:** Crashes at `openminion/services/gateway/security.py:132` with:
  ```text
  RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)
  ```
- **Expected:** Either (a) default `agent.default_channel` to `"console"` in the config parser when omitted, or (b) log a warning instead of raising when `mode="warn"`.

---

## Finding 3 (Bug): Wrong Field Name in `ConfigError` for `context.identity_budget`

- **Upstream Issue:** https://github.com/openminion/openminion/issues/875
- **Repro:** Set `"context": {"identity_budget": 100}` in `agents.json` and instantiate `Agent(config_path=...)`.
- **Actual:** `openminion/base/config/parser/budget.py:48` raises:
  ```text
  openminion.base.config.base.ConfigError: context.budget must be an object
  ```
- **Expected:** The error message should reference `context.identity_budget` (the actual schema key) and ideally show the expected object shape (`{"max_tokens": ..., ...}`).

---

## Finding 4 (DX Friction): CLI Provider Drift Between `setup --list-providers` (20) and `config init --provider` (9)

- **Upstream Issue:** https://github.com/openminion/openminion/issues/876
- **Repro:**
  1. Run `openminion setup --list-providers --json` → returns **20** providers including `cortensor-portal`, `cortensor-router`, `custom-openai-compatible`, `gemini`, `deepseek`, `mistral`.
  2. Run `openminion config init --provider cortensor-portal` (or `custom-openai-compatible`) → rejected by `argparse` because `--provider` only allows `{echo,openai,anthropic,claude,openrouter,cerebras,groq,ollama,cortensor}`.
- **Suggested Fix:** Generate the `config init --provider` choices dynamically from the same canonical provider registry used by `openminion setup --list-providers`.

---

## Finding 5 (DX Friction): Lazy Top-Level Exports Hide Public Symbols From `dir(openminion)`

- **Repro:** Run `python -c "import openminion; print([x for x in dir(openminion) if not x.startswith('_')])"`.
- **Actual:** Prints only `['Any', 'OPENMINION_VERSION', 'PROVIDER_ERROR_PUBLIC_VERSION', 'TURN_TIMEOUT_ERROR_PUBLIC_VERSION', 'TYPE_CHECKING', 'base', 'import_module']`.
- **Suggested Fix:** Add `__dir__()` (and `__all__`) to `openminion/__init__.py` returning the lazy-exported public API (`Agent`, `APIRuntime`, `tool`, `subagent`, `Handoff`, `ProviderError`, `AgentOutputValidationError`, `TurnTimeoutError`) so IDE autocomplete and Python REPL introspection work seamlessly.
