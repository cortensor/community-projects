# Release History

## v0.1.0 (2026-11-27)

- Initial release for Cortensor Hackathon #5 (`openminion==0.1.24`).
- Added 5-case OpenMinion evaluation pipeline (`probe_inference_endpoint`, `subagent`, `FailClosedApprovalGate`, `session_id` continuity, `EvalReport` Pydantic output).
- Added `MemoryBundle` export/reload verification and `facts.json` / `report.md` artifact generation.
- Added Cortensor Portal reachability probe example (`examples/cortensor-portal-probe/`) and end-to-end mock OpenAI server `pytest` suite (`3/3` passing).
