# What We Learned (`openminion==0.1.24`)

## Verified Findings & Reproducers

1. **`subagent(parent, ...)` drops `parent.agent_id` (`openminion/api/handoff.py:299-307`)**
   - **Observed Behavior:** When a parent `Agent` is constructed with an explicit `agent_id="evaluator"`, calling `subagent(parent, name="reviewer", ...)` constructs the child `Agent` without forwarding `agent_id=parent.agent_id`. Consequently, `child.agent_id` evaluates to `None` and the child falls back to the config `default_agent` profile instead of inheriting the parent's `agent_id` / `provider_policy` / model connection.
   - **Reproducer:** Automated test `test_openminion_subagent_agent_id_finding_reproducer` in `tests/test_eval_suite.py`.
   - **Suggested Fix:** Forward `agent_id=parent.agent_id` inside `openminion.api.handoff.subagent()`.

2. **Minimal `agents.json` without `default_channel` fails inside `GatewaySecurity`**
   - **Observed Behavior:** Hand-crafting a minimal `agents.json` (`{"default_agent": "demo", "agents": {"demo": {"provider": "echo"}}}`) without `agents.<id>.default_channel = "console"` raises `RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)` during `Agent.run()`.
   - **Workaround / Takeaway:** Always bootstrap configurations with `ProviderSetupRequest` + `build_provider_setup` (which sets `default_channel: "console"`), or surface an explicit `ConfigError` at config load time when `default_channel` is empty.

3. **`ProviderSetupRequest` credential gating before `APIRuntime` initialization**
   - **Observed Behavior:** `build_provider_setup` raises `ProviderSetupMissingCredential` before `APIRuntime` even initializes if the preset requires a credential env var (e.g., `cortensor-portal`) and none is set.
   - **Takeaway:** Separating read-only endpoint reachability probing from `APIRuntime` bootstrap allows tools to report live HTTP status (`https://api.cortensor.app/v1/models -> HTTP 401 in ~1.1 s`) and cleanly enter deterministic offline fallback without crashing.

4. **Cortensor Portal Probe (`https://api.cortensor.app/v1/models`)**
   - Non-destructive `GET /models` reaches Cortensor Portal cleanly (`HTTP 401` without API key, ~1.1 s round-trip), verifying TLS/network transport and clean `ProviderError` / `AUTH_ERROR` surface with `Provider request ID`.
