# What We Learned — Actionable OpenMinion 0.1.24 Engineering Feedback

Empirical findings captured against `openminion==0.1.24` on Python 3.12 during Cortensor Hackathon #5 (`#2418`). Every item includes exact module paths, observed runtime behavior, reproduction mechanics, and a concrete upstream fix.

## 1. [OM-FINDING-01] Minimal agents.<id> block omits default_channel and fails inbound authenticity in warn mode (`HIGH`)

- **Component:** `openminion/services/gateway/security.py:132 & base/config/core.py:124`
- **Observed Behavior:** Writing a custom agents.<id> entry without 'default_channel': 'console' (matching README.md lines 192-199) leaves AgentProfileConfig.default_channel='' and raises RuntimeError('inbound authenticity denied (reason=invalid_channel, mode=warn)').
- **Recommended Upstream Fix:** Default Agent._build_payload or AgentProfileConfig.default_channel to 'console' for embedded Python SDK calls so minimal agents.json profiles run out of the box.

## 2. [OM-FINDING-02] Setting human display string in agents.<id>.name triggers UnknownProfileError (`MEDIUM`)

- **Component:** `openminion/services/runtime/ingress/timeout.py:54 & base/config/core.py:407`
- **Observed Behavior:** Configuring 'agents': {'gemini-live': {'name': 'Gemini Live', ...}} causes runtime profile lookup during timeout calculation to pass display name 'Gemini Live' instead of key 'gemini-live', raising UnknownProfileError.
- **Recommended Upstream Fix:** Separate immutable profile_id (dict key) from human display_name in AgentProfileConfig and resolve_runtime_profile.

## 3. [OM-FINDING-03] Sequential Agent.run calls on one session_id fork threads unless thread_id is passed (`MEDIUM`)

- **Component:** `examples/sdk/sessions.py:18-19 & openminion/api/agent.py:167-170`
- **Observed Behavior:** Calling second = agent.run(...) on the same Agent(session_id='shared') without thread_id=first.thread_id sets thread_decision_action='fork_thread' (settled_without_resume) and session_history_available='false', hiding prior turn messages until thread_id is supplied.
- **Recommended Upstream Fix:** Either auto-carry last_thread_id inside stateful Agent instances when session_id matches, or update examples/sdk/sessions.py to pass thread_id=first.thread_id explicitly.

## 4. [OM-FINDING-04] Setup catalog provider IDs differ from agents.json SUPPORTED_PROVIDERS keys (`MEDIUM`)

- **Component:** `openminion setup --list-providers vs modules/llm/providers/factory.py:28`
- **Observed Behavior:** CLI setup lists 20 catalog IDs ('gemini', 'cortensor-portal', 'cortensor-router'), while SUPPORTED_PROVIDERS in agents.json only accepts 9 transport keys ('openai', 'cortensor', etc.). Cortensor Portal uses 'openai' with max_retries=0 (cortensor_portal_no_idempotency).
- **Recommended Upstream Fix:** Accept catalog aliases in OpenMinionConfig.from_dict and normalize them to transport + base_url overrides automatically, or surface the canonical agents.json snippet in setup --list-providers --json.

## 5. [OM-FINDING-05] Single tool turn triggers 7 internal LLM calls and Ollama defaults to fallback tool parsing (`LOW`)

- **Component:** `modules/brain/loop & base/config/providers.py:85`
- **Observed Behavior:** Telemetry metadata ('llm_call_counts_by_purpose') records 7 LLM calls (entry=1, freshness_classify=1, act=3, reflect=1, judge=1; ~16.4k input tokens) for 1 tool call, multiplying decentralized Cortensor router latency ~7x.
- **Recommended Upstream Fix:** Add a 'fast_single_pass' profile skipping post-turn reflect/judge/freshness calls on bounded SDK tool workflows, and switch OllamaProviderConfig.tool_call_strategy default to 'hybrid'.

## Reproduction Command

```bash
.venv/bin/python -m src.cli
.venv/bin/pytest tests -q
```
