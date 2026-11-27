# OpenMinion SDK workflow

1. `Agent(agent_id, instructions, tools=[load_seen_job_ids], forced_tools=["load_seen_job_ids"], session_id=...)` then `agent.run(prompt)`: a real, verifiable tool call.
2. Feed fetching uses plain `@tool` functions (`fetch_remotive_jobs`, `fetch_arbeitnow_jobs`, `fetch_hn_hiring_jobs`) called in-process.
3. `APIRuntime.from_config_path(config).llm.client.complete(messages, max_tokens=4096)` does the shortlist.
4. `ProviderError` handling with retries and a fallback config.
