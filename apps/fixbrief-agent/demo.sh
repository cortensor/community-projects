#!/usr/bin/env bash
# FixBrief demo: real commands, real output.
# Prereqs: .venv with requirements installed; for the model steps, a
# local OpenAI-compatible server on 127.0.0.1:8000, e.g. llama.cpp:
#   .venv/bin/pip install llama-cpp-python
#   .venv/bin/python -m llama_cpp.server \
#     --model qwen2.5-1.5b-instruct-q4_k_m.gguf \
#     --host 127.0.0.1 --port 8000 --n_ctx 8192 &
# (Ollama also works: swap --provider ollama --model qwen2.5:1.5b.)
set -euo pipefail
cd "$(dirname "$0")"

export FIXBRIEF_BASE_URL="${FIXBRIEF_BASE_URL:-http://127.0.0.1:8000/v1}"
export FIXBRIEF_API_KEY="${FIXBRIEF_API_KEY:-local}"
MODEL="${FIXBRIEF_MODEL:-qwen2.5-1.5b-instruct-q4_k_m.gguf}"

.venv/bin/fixbrief --version
.venv/bin/python -m pytest tests/ -q
.venv/bin/fixbrief setup --provider openai --model "$MODEL"
.venv/bin/fixbrief doctor
.venv/bin/fixbrief brief --device "iPhone 12" --symptom "black screen" \
  --sample iphone-black-screen.md --offline
.venv/bin/fixbrief followup --session demo-live \
  --message "Use get_source_facts with kind=sample and locator=samsung-not-charging.md, then write a short repair summary in Spanish (5-8 sentences) covering likely causes and first diagnostic steps. Base it only on the tool facts." \
  --provider openai --model "$MODEL" --timeout 2400 --yes
.venv/bin/fixbrief followup --session demo-live \
  --message "In one sentence, what is the most likely cause?" \
  --provider openai --model "$MODEL" --timeout 2400 --yes
.venv/bin/fixbrief history
cat outputs/live_model_run_receipt.json
