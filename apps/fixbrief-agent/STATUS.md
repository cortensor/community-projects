# Status — FixBrief Agent

- **Version:** 0.1.0
- **Status:** active (Cortensor Hackathon #5 submission)
- **SDK:** OpenMinion 0.1.24 (`openminion==0.1.24`), Python 3.11+
- **Demo provider:** llama.cpp (`llama-cpp-python`) + Qwen2.5-1.5B-Instruct GGUF via OpenMinion's `openai` provider (free, local, no credentials)
- **Tests:** 27 offline tests passing (`pytest tests/ -q`)

## Roadmap

- More bundled repair samples (water damage, no signal, touch faults)
- Optional Cortensor Portal run once a hackathon API key is available
- Batch mode: one brief per (device, symptom) row from a CSV

## Known issues

- Fact extraction is heuristic; unusual source layouts may miss steps.
- Brief wording quality depends on the chosen model; small local
  models occasionally produce terse summaries (schema still validates).
- Live-URL fetching uses a minimal HTML-to-text pass; JS-rendered
  pages return little text (use `--sample` or a static URL).
