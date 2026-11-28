# Cortensor Agent Eval Report — openminion-core-v1

- **Verdict:** `READY` (100/100)
- **Provider / Model:** `openai` / `mock-eval-model`
- **Endpoint Probe:** `http://127.0.0.1:7847/v1/models` -> `HTTP 200` (358.32 ms)
- **Session ID:** `cortensor-h5-e2e-001` (persisted=True)
- **Offline Fallback Used:** `False`

## Benchmark Cases

| Case ID | Category | Passed | State | Latency (ms) | Detail |
| --- | --- | --- | --- | --- | --- |
| `case_probe_tool` | `tool_calling` | `True` | `completed` | 1657.2 | probe_count=2 |
| `case_subagent_delegation` | `delegated_subagent` | `True` | `completed` | 1203.4 | child_session=3a8014f0332547b29cf62ea9c7c8499c |
| `case_approval_gated_write` | `policy_gate` | `True` | `completed` | 1222.3 | approvals=1 |
| `case_session_continuity` | `session_continuity` | `True` | `completed` | 414.8 | session_id=cortensor-h5-e2e-001, stream_events=9 |
| `case_structured_judge` | `structured_output` | `True` | `completed` | 834.0 | verdict=READY, score=100 |

## Approval Gate Audit

- `write_eval_artifact` (`tc3`): **approved** — single_use_artifact_write_approved

## Judge Summary

All 5 OpenMinion benchmark cases passed cleanly.
