# What We Learned (`openminion==0.1.24`)

Actionable engineering notes from building and testing **ProofAudit Minion** on `openminion==0.1.24` (Windows 11 + Python 3.12).

## 1. Windows Global `PYTHONHOME` Sensitivity
- If a host machine has `PYTHONHOME` set globally (for example to an older Python 3.8 install), invoking an isolated Python 3.12 `.venv\Scripts\python.exe` fails immediately with `AssertionError: SRE module mismatch` in `sre_compile.py`.
- **Workaround**: Clear `PYTHONHOME` and `PYTHONPATH` before running `.venv\Scripts\python.exe` or `openminion.exe`.
- **Recommendation**: Consider documenting this in the Windows install notes or stripping conflicting `PYTHONHOME` inside the `openminion` CLI launcher.

## 2. Programmatic Provider Switching & `custom-openai-compatible`
- `Agent` and `APIRuntime` do not take `provider` or `base_url` as direct constructor keyword arguments; instead they read `agents.json` via `APIRuntime.from_config_path(...)`.
- Using `openminion.services.bootstrap.provider_setup` (`ProviderSetupRequest`, `build_provider_setup`, `atomic_save_setup_config`) with an isolated `TemporaryDirectory` (`home_root` + `data_root`) is a clean, reliable way to switch between `openrouter`, `cortensor-portal`, `cortensor-router`, and `custom-openai-compatible` without mutating the user's global `~/.openminion` config.

## 3. `@tool` Scope Classification & `approval_callback`
- `@tool(min_scope="READ_ONLY", idempotent=True)` runs automatically without prompting `approval_callback` under the default `action_policy` (`allow_read_only_without_prompt: true`).
- Omitting `min_scope="READ_ONLY"` (e.g. `@tool(idempotent=True)` for `run_repo_smoke_check`) classifies the tool as a reversible local write, which reliably triggers `approval_callback(tool_name, args, approval_id)` during `Agent.run(...)`.
- This distinction is well documented in `openminion.tools.decorator`, and surfacing it in SDK examples alongside `Agent.run(..., approval_callback=...)` would help developers wire gated tools faster.

## 4. `cortensor-portal` & `cortensor-router` Discovery
- `openminion setup --list-providers --json` already exposes both `cortensor-portal` (`https://api.cortensor.app/v1`, `CORTENSOR_API_KEY`, `oss-20b`) and `cortensor-router` (`http://127.0.0.1:8080/api/v2/completions`, `CORTENSOR_API_KEY`, `gpt-oss-20b`).
- Because hosted/decentralized endpoints can occasionally return HTTP 5xx or refuse strict JSON schemas/tool calls, pairing `ProviderError` + `AgentOutputValidationError` handling with a deterministic offline fallback keeps CLI audits reliable and repeatable.

## Live Free-Tier Model Observations (`openminion==0.1.24`)
1. **`TurnTimeoutError` on slow/routed models**: `openrouter/free` routed to `liquid/lfm-3-1.7b:free` and hit `openminion.services.runtime.ingress.types.TurnTimeoutError: Turn execution timed out after 90.00 seconds` during multi-tool orchestration. Switching to `nvidia/nemotron-3.5-super-vl:free` completed both Stage 1 (`@tool` + `approval_callback`) and Stage 2 (`output_type=ProofAuditReport`) cleanly with `used_offline_fallback=False`.
2. **Upstream `429 Too Many Requests` (`ProviderError: RATE_LIMITED`)**: `google/gemma-4-31b-it:free` triggered upstream `429` across OpenMinion's built-in retries, surfacing a structured `ProviderError` (`RATE_LIMITED`) that our application caught and handled cleanly.
3. **Windows `openminion doctor --json` ergonomics**: When running with an isolated `--config <temp>/agents.json`, `openminion doctor --json` exits `0` cleanly and surfaces missing identity bundle diagnostics without crashing.
