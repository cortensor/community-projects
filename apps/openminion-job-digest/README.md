# openminion-job-digest

A small agent built on the OpenMinion 0.1 Python SDK. It does one repeatable job: pull remote job listings from three free public sources, skip jobs it already showed, and write a Markdown shortlist for a junior AI/software engineer.

Built for Cortensor Hackathon #5. Source repo: https://github.com/abdalla-dawoud/openminion-job-digest

## Workflow

1. A forced SDK tool call (`load_seen_job_ids`) reads the seen-store. The call goes through the `Agent` with `forced_tools`, so it is a real tool invocation.
2. The script fetches listings from Remotive, Arbeitnow and the latest Hacker News "Who is hiring?" thread (Algolia API). No API keys are needed for these.
3. It removes seen jobs and obvious senior titles, then asks the model to pick up to 5 fits through OpenMinion's runtime LLM client (`runtime.llm.client.complete`, `max_tokens=4096`).
4. The reply is validated with Pydantic, links are re-attached by id from the fetched data (the model never copies URLs), and `out/digest-YYYY-MM-DD.md` is written. New ids go to the seen-store.

## Setup

```bash
pip install -r requirements.txt
openminion setup --no-chat --provider groq --model qwen/qwen3.8-27b
export GROQ_API_KEY=...        # free tier, console.groq.com
```

Any OpenMinion provider works. `--fallback-config` takes a second `agents.json` that is tried if the first provider is rate limited or returns empty content.

## Run

```bash
python job_digest.py
```

## Notes

- Free model tiers are tight (see WHAT_WE_LEARNED.md). The demo run used Groq `qwen/qwen3.8-27b`.
- AI-assisted development: this project was built by an AI assistant for Abdalla Dawoud, who owns and publishes it.
- MIT license.
