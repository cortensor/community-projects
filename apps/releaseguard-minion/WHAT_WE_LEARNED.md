# What We Learned Building ReleaseGuard Minion on OpenMinion `0.1.24`

Building an inspectable, permission-gated release auditor on **`openminion==0.1.24`** for **Cortensor Hackathon #5** surfaced concrete engineering lessons about where OpenMinion excels today and where real-world operational agents hit sharp edges.

---

## 1. Risk-Tiered `@tool` Contracts + Fail-Closed Callbacks Are OpenMinion's Biggest Strength

Separating tool risk at the decorator layer — `min_scope="READ_ONLY", idempotent=True` vs. `WRITE_SAFE` vs. `dangerous=True` — let us keep ReleaseGuard Minion's security boundary declarative and auditable:
- `inspect_repo_manifest`, `inspect_ci_and_tests`, and `scan_secret_hygiene` execute automatically under OpenMinion's default `allow_read_only_without_prompt: true` policy.
- `write_release_brief` and `create_release_tag` always pass through `approval_callback`.
- Wrapping `approval_callback` in a single-use fail-closed ledger (`ReleaseApprovalGate`) gave us deterministic single-use write enforcement (`allowed_once:write_release_brief` on first call, `denied:single_use_brief_write_already_consumed` on retry) and an explicit audit trail (`ApprovalDecisionRecord`) without fighting the framework.

## 2. Typed Outputs (`output_type=BaseModel`) and Human-in-the-Loop Policy Confirmation Must Compose

Production DevOps and Web3 release agents almost always combine **typed structured outputs** (`Agent(output_type=ReleaseAuditReport)`) with **policy-gated side effects** (`write_release_brief`, `create_release_tag`). In `openminion==0.1.24`, those two primitives collide in two distinct ways:

1. **Schema field name collision ([`openminion#884`](https://github.com/openminion/openminion/issues/884)):** Our first draft of `ReleaseAuditReport` used standard fields `status` and `summary`. After executing read-only tools, OpenMinion's post-processor (`rules.py:110-135`) mistook the model's valid JSON output for leaked raw tool markup, discarded it, and forced plain-text retries until the turn failed with `AgentOutputValidationError`. Switching to `verdict` + `rationale` unblocked us, and we wrote a deterministic repro (`test_finding_1`) plus a narrow fix design (check actual tool-envelope keys like `tool_call_id`/`tool_name`, or skip raw-markup stripping when structured output is active).
2. **Confirmation pause/denial crash ([`openminion#883`](https://github.com/openminion/openminion/issues/883)):** When a tool triggers a confirmation pause (without `approval_callback`) or callback denial, `Agent._run_once()` (`api/agent.py:370`) unconditionally calls `_coerce_output(reply_text)` on `"Policy confirmation required..."` / `"Confirmation denied..."`. Raising `AgentOutputValidationError` swallows `result.thread_id`, breaking the documented pause-and-resume confirmation flow. Bypassing `_coerce_output()` when `metadata["respond_kind"]` indicates a confirmation pause/denial would make `output_type` + human-in-the-loop work cleanly out of the box.

## 3. Delegation (`subagent()`) Needs Explicit Profile & Policy Inheritance

When we added a bounded `secret-reviewer` child subagent (`tools=[scan_secret_hygiene]`, `timeout_seconds=60`) on a parent targeting `agent_id="auditor"`, the child silently executed against `default_agent` (`echo_default`) with zero warnings and zero HTTP calls to our auditor provider.

Inspecting `src/openminion/api/handoff.py:299-307` revealed that `subagent()` constructs the child `Agent(...)` without forwarding `agent_id=parent.agent_id`. That is a subtle security and correctness hazard whenever a parent profile has a stricter `action_policy` or different model than `default_agent`. We verified that community PR [`openminion#732`](https://github.com/openminion/openminion/pull/732) already fixes this upstream, kept our automated regression test (`test_finding_3`), and added a clean 2-line defensive guard in `ReleaseGuardMinion.run_security_subagent()` (`agent.py:246-247`) so our app works safely on `0.1.24` today.

## 4. Unix Pipe & `--json` Hygiene Matter When Agents Live in CI Pipelines

When wiring `openminion` CLI diagnostics into CI and shell workflows, we hit two immediate papercuts — and contributed surgical upstream PRs for both:

- **[`openminion#881`](https://github.com/openminion/openminion/issues/881) -> Fixed in [PR `#885`](https://github.com/openminion/openminion/pull/885):** Piping `openminion tools list | head -n 5` exited `1` with `openminion: internal error: BrokenPipeError: [Errno 32] Broken pipe` because `BrokenPipeError` inherits from `OSError` in `_TERMINAL_CLI_ERRORS`. Our PR catches `BrokenPipeError` explicitly, silences teardown stdout flush noise when `owns_process=True`, and exits `0` (`36/36` tests passing, all repo quality validators clean).
- **[`openminion#882`](https://github.com/openminion/openminion/issues/882) -> Fixed in [PR `#886`](https://github.com/openminion/openminion/pull/886):** Running `openminion doctor --check-turn --json` emitted ~`9.7 KB` of `INFO` bootstrap/Alembic logs onto `stderr`. Our 1-line fix reuses `logging_mode="interactive"` when `--json` is active, yielding clean stdout JSON and zero-byte stderr (`29/29` tests passing, including a subprocess regression test).

## 5. Testing Through the Real HTTP Transport Pays Off Immediately

Instead of mocking `Agent.run()` or relying solely on OpenMinion's built-in `echo` provider (which bypasses tool calling), building a tiny stdlib `LocalOpenAIServer` (`tests/conftest.py`) behind `providers.openai.base_url` forced every test run through OpenMinion's real `httpx`/`llmctl` client, brain loop, tool post-processor, policy gate, SQLite migrations, and streaming layer. Every single one of Findings `#1–#4` was uncovered directly because our tests exercised the real runtime end-to-end.

## 6. Provider-Neutral Cortensor Readiness Is Seamless via `agents.json`

Keeping provider configuration completely outside application code — letting operators run `openminion setup --provider cortensor-portal --model oss-20b --no-chat`, `cortensor-router`, `groq`, `gemini`, or any OpenAI-compatible endpoint — eliminated provider lock-in and kept secrets strictly out of the app codebase. One subtle setup detail worth calling out: minimal hand-written `agents.json` profiles must include `"default_channel": "console"` on `0.1.24` (tracked upstream in [`openminion#874`](https://github.com/openminion/openminion/issues/874) / [PR `#864`](https://github.com/openminion/openminion/pull/864)), otherwise inbound channel authenticity rejects turns with `reason=invalid_channel`.
