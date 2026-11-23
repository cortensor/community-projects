# What We Learned — Actionable Feedback for OpenMinion / Cortensor

From building FixBrief (a multilingual repair-brief agent) on
OpenMinion 0.1.24 for Cortensor Hackathon #5.

## What worked well

1. **The "code collects facts, model reasons" pattern fits the SDK.**
   Run-scoped `@tool` functions + `forced_tools` + `output_type` gave a
   verifiable pipeline: facts are deterministic and unit-testable, the
   model's job is bounded to structuring + language. For a small local
   model this is the difference between a demo and a hallucination.
2. **Typed output with prose tolerance.** Accepting one JSON object
   wrapped in prose (0.1.x compatibility) makes pydantic-validated
   output realistic with 1–3B local models.
3. **Tools stay plain callables.** Being able to unit-test
   `get_source_facts` without the runtime kept the test suite fast and
   fully offline.
4. **Receipts are genuinely useful.** `AgentRunResult.stats/metadata`
   (tokens, tool calls, durations, run/session/thread IDs) made it
   trivial to emit an honest run receipt for judges.

## What should improve (ranked by builder impact)

1. **Give `echo` a tool-executing mode.** Today `forced_tools` is a
   silent no-op under echo (`tool_calls: 0`), so the most important
   wiring (tool registration, approval, forced first call) cannot be
   tested without a real model. A deterministic fake-model provider
   that emits canned tool calls + canned JSON would make every
   hackathon project's CI meaningful. This is the single highest-value
   addition for builders.
2. **Document the approval callback with an example.** The
   `(tool_name, args, approval_id) -> bool` contract currently requires
   reading `api/agent.py`. Add `examples/sdk/approval_gate.py` showing
   READ_ONLY auto-run vs. write-tool confirmation vs. denial.
3. **Raise or surface the Ollama timeout.** The generated config's 60 s
   provider timeout is too low for CPU inference with tool loops;
   builders will hit `ProviderError`/timeouts and blame the SDK. Either
   default Ollama to ~300 s or print the knob during `setup`.
4. **One-line install note for small `/tmp`.** `pip install openminion`
   fails with ENOSPC on 512 MB tmpfs `/tmp` (common in containers).
   Document `TMPDIR`/`PIP_CACHE_DIR` on disk in the install section.
5. **Make `setup --list-providers` show credential-free paths first.**
   For hackathons, "which provider can I run right now with no account?"
   is the first question. Ollama/echo deserve a "no credential needed"
   badge at the top (the JSON output could carry `credential: null`).

## Product feedback for Cortensor Portal (from the brief, not hands-on)

Portal was optional for qualification and access is coordinated, so
this entry uses a local llama.cpp model (Qwen2.5-1.5B GGUF) and keeps
`cortensor-portal` as a
one-command provider swap (`fixbrief setup --provider
cortensor-portal`, `CORTENSOR_API_KEY` via env). A self-serve,
rate-limited **free Portal key for hackathon participants** (even
50 requests) would let every entrant test the hosted path the brief
encourages, instead of only teams with coordinated access. The SDK
side is already ready: same agent code, different provider string.

## Lessons we would carry to the next agent

- Ground first, generate second: deterministic tools + schema
  validation beat prompt engineering, especially with small models.
- Label provenance in the data model itself (`generated_by`), not in
  prose — judges and users should never have to guess what ran.
- Test the failure taxonomy, not just the happy path: provider down,
  invalid JSON, and timeout are three different user stories and the
  SDK already separates them cleanly.
