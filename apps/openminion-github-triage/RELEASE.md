# Release History

## v0.1.0 (2026-11-21)

- Initial release for Cortensor Hackathon #5.
- Implemented read-only GitHub REST ingestion (`github_source.py`) and Pydantic `openminion-triage.v1` output schemas (`models.py`).
- Wired `@tool`, `derive_tool_specs`, `ToolRegistry.execute_calls`, `ProviderToolCall`, `SQLiteSessionStore`, `TaskState`, and `PhaseStatus` (`orchestrator.py`).
- Persisted final assistant turns in `SQLiteSessionStore` across both issue and release workflows.
- Added reasoning-tag stripping and higher completion budget (`512` tokens) in `llm.py` for OpenAI-compatible reasoning models.
- Verified with 11 passing offline tests and live `openai/gpt-oss-120b` runs on fixture `#42` and `openminion/openminion#236`.
