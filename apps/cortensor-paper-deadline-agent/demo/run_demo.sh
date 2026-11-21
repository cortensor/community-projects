#!/usr/bin/env bash
# Demo: deadlines (120 days) + brief (topic 人工智能) on the real tables.
# Zero LLM cost for the deadlines step; the brief step uses the free
# Pollinations endpoint by default (paced for its 1-reply-per-45s limit,
# so the brief takes a few minutes). Use --no-model for a template-only
# run:  PAPER_WATCH_DEMO_NO_MODEL=1 ./demo/run_demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/paper-watch ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -e .
fi

export PAPER_WATCH_MEMORY="${PAPER_WATCH_MEMORY:-$(mktemp -d)/reminded.json}"

echo "=== 1. Deadlines in the next 120 days (new reminders only) ==="
.venv/bin/paper-watch deadlines --within-days 120

echo ""
echo "=== 2. Same command again: 0 new reminders (memory dedup) ==="
.venv/bin/paper-watch deadlines --within-days 120

echo ""
echo "=== 3. Research brief: 人工智能 ==="
if [ "${PAPER_WATCH_DEMO_NO_MODEL:-0}" = "1" ]; then
  .venv/bin/paper-watch brief --topic 人工智能 --no-model
else
  .venv/bin/paper-watch brief --topic 人工智能 \
    --save-record "fixtures/live_run_$(date +%Y-%m-%d)_brief-ai.json"
fi

echo ""
echo "Demo done."
