# Real model run: local Ollama llama3.2:3b

Date: 21 Nov 2026, 7:14:16 AM to 7:18:40 AM WAT (Africa/Lagos)
Command: `python -m minion_radar --demo-data --yes --out samples`
Provider: OpenMinion 0.1.23 preset `ollama` at `http://127.0.0.1:11434` (no API key)
Model: `llama3.2:3b` created locally from the public Hugging Face GGUF `bartowski/Llama-3.2-3B-Instruct-GGUF` (`Llama-3.2-3B-Instruct-Q4_K_M.gguf`)
Why not official `llama3.1`: `ollama pull llama3.1` failed on this machine because the Ollama registry blob host resolved to a non-public address (`198.18.0.1`) and Ollama refused the redirect. The Hugging Face file downloaded successfully with curl.
Mode: real model, SIMULATED fixture repo data (`--demo-data`)
Agent id: `radar`
Run id: `d23ed39620d846e1953cadbf324161d9`
Elapsed: 263644 ms (about 4 minutes 24 seconds)
LLM calls: 10 (act 5, entry 2, freshness_classify 1, judge 1, reflect 1)
Tokens reported: 25642 input, 1595 output
Hardware: CPU-only box, about 15 GiB RAM, 8 vCPUs, no GPU

## Result: tools succeeded, structured output failed

This is a real model-backed run, but it is not a passing demo. OpenMinion raised `AgentOutputValidationError` because the final reply was Markdown, not JSON that validates as `BuilderBrief`. The CLI did not write a brief file.

All three tools ran and succeeded, in this order:

1. `radar_new_issues`
2. `radar_new_releases`
3. `radar_save_checkpoint` (auto-approved with `--yes`)

The local checkpoint was written under `.radar/` (gitignored) with fixture ids 9000, 9001 and issues 7001-7003, so the model did use the tool results. The fixture facts in the raw reply below (v9.9.1, v9.9.0, issues 101-103) match the simulated dataset.

OpenMinion also logged this warning at start:

```
memory.build_context_with_metadata failed agent_id=radar session_id=minion-radar:openminion/openminion error=invalid scope: 'session:minion-radar:openminion/openminion'
```

The `/` in the default GitHub repo session id appears to break memory scope parsing. That is a useful building-block finding, not a blocker for a later demo if we change the session id format.

## Raw model reply (invalid as BuilderBrief)

```
radar: **BuilderBrief**

* Release: v9.9.1 - Breaking change to tool registry, migration guide included. (High)
* Release: v9.9.0 - Faster sessions. (Low)
* Issue: #101 - SIMULATED: streaming tool call drops arguments. (Bug, High)
* Issue: #102 - SIMULATED: docs typo. (Closed, Low)
* Issue: #103 - SIMULATED: deprecate legacy provider id. (Open, Medium)

**Next Steps**

1. Review the migration guide for the tool registry change.
2. Test the faster sessions feature.
3. Investigate the issue with the streaming tool call.
4. Verify the deprecation of the legacy provider id.

**Risk Level**

* High: Breaking change to tool registry, migration guide included.
* Medium: Deprecation of legacy provider id.
* Low: Faster sessions, Closed issue.

**Open Issues**

1. #101 - SIMULATED: streaming tool call drops arguments.
2. #103 - SIMULATED: deprecate legacy provider id.

**Recent Releases**

1. v9.9.1 - Breaking change to tool registry, migration guide included.
2. v9.9.0 - Faster sessions.

**Recent Issues**

1. #101 - SIMULATED: streaming tool call drops arguments.
2. #102 - SIMULATED: docs typo.
3. #103 - SIMULATED: deprecate legacy provider id.
```

## CLI error

```
OpenMinion run failed: AgentOutputValidationError: Reply did not validate against BuilderBrief: 1 validation error for BuilderBrief
  Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='radar: **BuilderBrief**\...ate legacy provider id.', input_type=str]
```

## Takeaway

Minion Radar can talk to a real local Ollama model with no secrets. A 3B model is weak for the required structured `BuilderBrief` JSON. A qualifying demo still needs a stronger model, such as official Ollama `llama3.1` on a machine that can pull it, or a hosted provider key (Cortensor Portal, OpenAI, OpenRouter, and others).
