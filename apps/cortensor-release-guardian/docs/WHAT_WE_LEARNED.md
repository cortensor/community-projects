# What We Learned — Actionable Feedback for OpenMinion `0.1.24` & Cortensor Builders

Every item below was reproduced directly on Windows 11, Python `3.14.1`, and `openminion==0.1.24` while building and running `cortensor-release-guardian` against both offline `echo` and a live `gemini-3.1-flash-lite` model.

1. **Bug #1: Omitting `default_channel` Crashes Programmatic `Agent.run()`:**
   - **Location:** `openminion/services/runtime/ingress/requests.py:116` & `openminion/services/gateway/security.py:132`
   - **Reproduction:** Load a minimal `agents.json` without `default_channel` via `APIRuntime.from_config_path(...)` and call `Agent(runtime=runtime, ...).run("...")`.
   - **Actual:** `channel` resolves to `""` and `GatewaySecurity.enforce_inbound_authenticity()` raises `RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)` even though `mode='warn'`.
   - **Expected:** Programmatic `Agent.run()` should default `channel` to `"api"` or `"cli"`.
   - **Workaround:** Set `"default_channel": "cli"` under `agents.<id>` (our `check_openminion_config` tool now flags missing `default_channel` automatically).

2. **Bug #2: Setup Catalog vs Provider Factory Mismatch (`gemini`):**
   - **Location:** `openminion setup --list-providers` vs `openminion/modules/llm/providers/factory.py:379`
   - **Actual:** `setup --list-providers` lists `gemini` as a supported provider, but configuring `"provider": "gemini"` raises `ProviderError: Unknown provider 'gemini'. Supported: anthropic, cerebras, claude, cortensor, echo, groq, ollama, openai, openrouter`.
   - **Expected:** Either accept `"provider": "gemini"` directly in `factory.py` or document the `"provider": "openai"` + custom `base_url` mapping.

3. **Bug #3: `env:VAR_NAME` Not Expanded Under `providers.openai.api_key` & Model Precedence:**
   - **Actual:** Setting `"api_key": "env:GEMINI_API_KEY"` under `providers.openai` sends the literal string `"Bearer env:GEMINI_API_KEY"` (HTTP 400 `INVALID_ARGUMENT`). Additionally, `providers.openai.model` must be set alongside `agents.<id>.model` or requests fall back to `gpt-4.1-mini` (HTTP 404 on non-OpenAI endpoints).
   - **Expected:** Expand `env:` references consistently across `providers.*` and honor `agents.<id>.model` over provider defaults.

4. **Rough Edge #4: `output_type=BaseModel` + Agent Prefix & Schema Injection:**
   - **Location:** `openminion/api/agent.py:253` (`_coerce_output`)
   - **Actual:** Live replies are prefixed with `"<agent_id>: "` (e.g., `"guardian-gemini: ### Release Readiness Decision: GO"`), and `output_type=ReleaseVerdict` does not automatically inject JSON schema instructions into the provider call, causing `AgentOutputValidationError` unless the caller adds explicit JSON formatting instructions and handles fallback.
   - **Expected:** Automatically append the Pydantic JSON schema to system instructions when `output_type` is a `BaseModel` and strip the `<agent_id>:` display prefix before JSON extraction.

5. **Windows PowerShell & Dependency Ergonomics:**
   - Adding a 4-line Windows PowerShell bootstrap snippet to `docs/getting-started.md` (`$env:OPENMINION_HOME = $PWD`) and moving `pillow` into an optional `openminion[vision]` extra would eliminate onboarding friction on Windows environments.
