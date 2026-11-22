# Building Blocks Tested — OpenMinion `0.1.24`

Environment: Windows 11, PowerShell 5.1, Python `3.14.1`, `openminion==0.1.24`, live model **`gemini-3.1-flash-lite`** via OpenAI-compatible endpoint (`HTTP/1.1 200 OK`, session `hack5-live-demo`) + offline `echo` provider for `pytest`.

| Building Block | API / Surface Tested | Status | Verified Result |
|---|---|---|---|
| **Package Install & CLI** | `pip install openminion`, `openminion --version`, `openminion setup --list-providers` | Worked (with caveat) | Lists 19+ providers including `cortensor-portal`, `cortensor-router`, `ollama`, `gemini`. Minor `pillow<13` pin conflict on existing media environments. |
| **Application Runtime** | `APIRuntime.from_config_path(...)` + `Agent(runtime=...)` | Bug Found + Workaround | Omitting `"default_channel"` crashes with `inbound authenticity denied (reason=invalid_channel, mode=warn)` (`requests.py:116`). Adding `"default_channel": "cli"` resolves it cleanly. |
| **Provider Factory & Switching** | `providers.openai` + `configs/agents.{gemini,ollama,cortensor-portal,echo}.json` | 2 Bugs Found + Worked | `"provider": "gemini"` rejected by `factory.py:379`; `"api_key": "env:..."` under `providers.openai` not expanded. Using `provider: openai` + `base_url` + `OPENAI_API_KEY` succeeded (`HTTP/1.1 200 OK`). |
| **Custom `@tool` + `forced_tools`** | `@tool(min_scope="READ_ONLY", idempotent=True)` + `forced_tools=["scan_repo_structure"]` | Worked | All 4 read-only tools registered cleanly and ran without interactive confirmation under `action_policy.allow_read_only_without_prompt: true`. |
| **Durable Sessions** | `Agent(..., session_id="hack5-live-demo")` across `audit` -> `followup` | Worked | Session persisted in SQLite under `OPENMINION_DATA_ROOT`; follow-up turn (`run_id=901885296c29419eba5dc6586a4a2958`) completed with `HTTP/1.1 200 OK`. |
| **Structured Output** | `output_type=ReleaseVerdict` + `AgentOutputValidationError` | Rough Edge + Fallback | OpenMinion prefixes replies with `<agent_id>: ` and does not auto-inject Pydantic JSON schema; our `AgentOutputValidationError` fallback preserved the full live `GO (100/100)` verdict cleanly. |
| **Automated Test Suite** | `pytest -v` (7 unit + live OpenMinion runtime tests) | Passed | `7 passed in 12.23s` on Python 3.14.1. |
