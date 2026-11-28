# Status

- **Version:** v0.1.0 (Cortensor Hackathon #5 submission)
- **State:** Working end-to-end. Real model-backed runs recorded in `examples/`
  (run 1: full triage; run 2: memory skip/re-triage behaviour).
- **SDK:** `openminion==0.1.24` (Python 3.12.3)
- **Recorded model path:** Ollama + `qwen2.5:3b` (local, no API key). Any
  OpenMinion provider preset can be substituted via `--provider/--model`.

## Roadmap

- Optional `--post` mode (still approval-gated) that applies labels/comments
  via the GitHub API for maintainers who want write-back.
- Batch mode across several repos with a shared digest report.
- Delegation: a second read-only agent that double-checks `critical` verdicts.

## Known issues

- Small local models occasionally skip the `get_issue` tool call or return a
  verdict without persisting it — the run log flags both cases
  (`tool-persisted=false`) instead of hiding them. See `FINDINGS.md`.
- One issue per agent turn keeps prompts small; very long issue bodies are
  truncated at 3000 chars by the `get_issue` tool.
