# Building Blocks Tested (`OpenMinion 0.1.24`)

| OpenMinion Building Block | How NovaTriage Minion Exercises It | Status | Notes |
| --- | --- | --- | --- |
| **Agent Execution & Streaming** | `Agent`, `APIRuntime`, `Agent.run()`, `Agent.run_stream(on_delta=...)`, Pydantic `output_type=NovaTriageReport` | Worked | `stream_events_seen=43` on live run; `_extract_json_object` strips `"default: "` prefix cleanly. |
| **Models / Providers** | `OpenAIProvider` -> in-process `NovaTriageLocalModelServer` (`/v1/chat/completions`, `$0` cost) + `CortensorProvider` env config | Worked | Real HTTP JSON + native `tool_calls` round-trips; supports `NOVATRIAGE_PROVIDER=cortensor\|openai\|local`. |
| **Tools (`@openminion.tool`)** | 6 tools: `analyze_solidity_contract`, `fetch_token_onchain_preflight`, `probe_x402_endpoint`, `recall_triage_memory` (`READ_ONLY`), `write_triage_report` (`WRITE_SAFE`), `publish_emergency_freeze_notice` (`dangerous=True`) | Worked | Tool exposure profiles and risk classification enforce scopes automatically. |
| **Permissions & Policy** | `NovaTriageApprovalGate` wired to `approval_callback` | Worked with caveat | Single-use write approval & `dangerous=True` fail-closed denial work; `Handoff` defaults to `WRITE_SAFE`. |
| **Sessions & Multi-Turn** | SQLite session persistence (`session_id` + `thread_id`) across initial triage + `FOLLOWUP:` turn | Worked with caveat | Requires forwarding `thread_id=result.thread_id`; otherwise `Agent.run(session_id=...)` opens a fresh thread. |
| **Memory (`MemoryBundle`)** | `export_bundle`, `save_bundle`, `load_bundle`, `import_bundle` + `recall_triage_memory` tool | Worked | Run #2 cleanly recalls Run #1 verdict (`memory_hits`). |
| **Skills (`Skill` catalog)** | `Skill.ingest_text`, `SkillIngestAuthority.local_operator`, `admit_skill_version`, `match`, `render_snippet` | Worked with caveat | `render_snippet` requires `purpose` in `{"plan", "respond", "act", "verify"}`. |
| **Tasks (`task.schedule` / `TaskSurface`)** | `execute_task_control(..., tool_name="task.schedule")` + `TaskSurface.list_tasks(runs_limit=5)` | Worked with caveat | `task.list` uses `limit`, whereas `TaskSurface.list_tasks` expects `runs_limit`. |
| **Delegation (`subagent` & `Handoff`)** | `subagent()` bounded `SubagentRunContext` + peer `Agent` `Handoff`s (`solidity_auditor_minion`, `recon_minion`) | Partial / Workaround | Combining `subagent(parent)` directly inside `Handoff()` deadlocks shared `ToolRegistry`; giving `Handoff` peers separate `APIRuntime` instances works cleanly. |
| **Diagnostics** | `APIRuntime.runtime_posture()`, `runtime_self_model()`, `capability_report()`, `tool_inventory_report()` | Worked | Returns live posture, `106` tool inventory entries, and SQLite DB verification. |
