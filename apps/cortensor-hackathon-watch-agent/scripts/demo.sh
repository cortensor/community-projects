#!/usr/bin/env bash
# Demo: run the whole loop on fixtures + the bundled baseline, $0.
#
# 1. pytest (loopback stubs, zero LLM cost)
# 2. hackathon-watch list (reads the bundled 2026-11-16 baseline)
# 3. hackathon-watch check against fixture list pages (deterministic
#    parse + rule screen, no model calls) into a throwaway state dir
# 4. hackathon-watch probe --offline (building blocks, no live model)
# 5. One real free-model classification (Pollinations, no key, 1 call)
#    so the demo shows a live verdict, not just stubs.
#
# Nothing is registered, logged in, or paid for. The live call is paced
# by the client; the whole script takes ~1-2 minutes.
set -euo pipefail
cd "$(dirname "$0")/.."

# Sandbox workaround: bare/bracketed IPv6 entries in NO_PROXY break httpx.
export NO_PROXY=localhost,127.0.0.1
export no_proxy=localhost,127.0.0.1

echo "== 1. pytest =="
.venv/bin/pytest -q

echo
echo "== 2. baseline list (first 5) =="
.venv/bin/hackathon-watch list --limit 5

echo
echo "== 3. check on the live list pages (rules only, \$0) =="
echo "(Fresh throwaway state, no baseline seed, so every entry the live"
echo " pages list right now counts as 'new' for this demo run. Kaggle is"
echo " expected to report unavailable — its page is a reCAPTCHA wall.)"
.venv/bin/hackathon-watch check --sources dorahacks,devfolio,kaggle \
  --state-dir /tmp/hackathon-watch-demo-state --no-seed || true

echo
echo "== 4. probe (offline: no live model calls) =="
.venv/bin/hackathon-watch probe --offline

echo
echo "== 5. one live classification (Pollinations free, 1 call) =="
.venv/bin/python - <<'PY'
import sys
sys.path.insert(0, "src")
from hackathon_watch.config import resolve_provider
from hackathon_watch.llm_client import DirectClient
from hackathon_watch.models import HackathonEntry, SuitabilityVerdict
from hackathon_watch.suitability import build_classify_messages, verdict_tool_schema

entry = HackathonEntry(
    name="Cortensor Hackathon #5",
    url="https://dorahacks.io/hackathon/2418/detail",
    source="dorahacks",
    notes="Build a runnable agent with OpenMinion 0.1 SDK; online; $1,150 prize pool.")
client = DirectClient(resolve_provider("openai-compatible"))
verdict = client.classify(SuitabilityVerdict,
                          build_classify_messages(entry),
                          tools=verdict_tool_schema())
print(f"live verdict: label={verdict.label} reason={verdict.reason}")
print(f"model calls: {client.calls_made}, tokens: {client.tokens_used}, cost: $0")
PY

echo
echo "Demo done. Sample alert semantics: every verdict above is"
echo "PRELIMINARY and needs human confirmation on the official page"
echo "before anyone registers."
