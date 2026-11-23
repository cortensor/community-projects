"""Project-local OpenMinion configuration.

FixBrief keeps its OpenMinion home inside the project directory
(``.fixbrief-home/``) so runs are reproducible and never touch the
user's global ``~/.openminion`` config. ``ensure_config`` writes an
``agents.json`` for the requested provider by invoking the SDK's own
``openminion config init`` and then patching model/timeout fields.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOME_DIR = PROJECT_ROOT / ".fixbrief-home"
CONFIG_PATH = HOME_DIR / ".openminion" / "agents.json"
DATA_ROOT = HOME_DIR / "data"

# provider -> (default model, credential env var or None)
PROVIDERS: dict[str, tuple[str, str | None]] = {
    "ollama": ("qwen2.5:1.5b", None),
    "echo": ("echo", None),
    "openrouter": ("openai/gpt-4.1-mini", "OPENROUTER_API_KEY"),
    "openai": ("gpt-4.1-mini", "OPENAI_API_KEY"),
    "groq": ("llama-3.3-70b-versatile", "GROQ_API_KEY"),
    "cerebras": ("gpt-oss-120b", "CEREBRAS_API_KEY"),
    "cortensor-portal": ("oss-20b", "CORTENSOR_API_KEY"),
    "anthropic": ("claude-sonnet-5", "ANTHROPIC_API_KEY"),
    "gemini": ("gemini-3.6-flash", "GEMINI_API_KEY"),
}


def normalize_no_proxy() -> None:
    """Strip bracketed IPv6 entries from NO_PROXY (httpx parse bug).

    Some sandboxes export ``NO_PROXY=...,::1,[::1],...``; httpx raises
    ``InvalidURL: Invalid port: ':1]'`` when building its proxy patterns
    from that value, which would break provider HTTP calls (including
    Ollama on 127.0.0.1). Removing the bracketed forms keeps the same
    bypass semantics (bare ``::1`` remains). Idempotent.
    """
    for key in ("NO_PROXY", "no_proxy"):
        value = os.environ.get(key)
        if not value:
            continue
        entries = [e.strip() for e in value.split(",")]
        kept = [e for e in entries if e and not (e.startswith("[") and e.endswith("]"))]
        os.environ[key] = ",".join(kept)


def runtime_env() -> dict[str, str]:
    env = dict(os.environ)
    env["OPENMINION_HOME"] = str(HOME_DIR)
    env["OPENMINION_DATA_ROOT"] = str(DATA_ROOT)
    return env


def ensure_config(provider: str = "ollama", model: str | None = None) -> Path:
    """Create (or reuse) the project agents.json for ``provider``."""
    if provider not in PROVIDERS:
        raise ValueError(
            f"unknown provider {provider!r}; choose from {sorted(PROVIDERS)}"
        )
    default_model, _ = PROVIDERS[provider]
    chosen_model = model or default_model

    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        agents = data.get("agents", {})
        current = next(iter(agents.values()), {}) if agents else {}
        if current.get("provider") == provider:
            _patch_runtime(data)
            _patch_provider_model(data, provider, chosen_model)
            CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return CONFIG_PATH
        # Provider switch: `config init` without --force silently keeps
        # the old config (verified locally), so force the overwrite.

    HOME_DIR.mkdir(parents=True, exist_ok=True)
    env = runtime_env()
    # `config init` accepts fewer provider names than `setup`
    # (e.g. no "cortensor-portal"); initialize with the closest name
    # and then set the agent's provider field to the requested one.
    init_provider = {"cortensor-portal": "cortensor"}.get(provider, provider)
    cmd = [
        sys.executable, "-m", "openminion",
        "config", "init", "--provider", init_provider, "--force",
    ]
    # `openminion` console script is the documented entry point; fall back
    # to it if `python -m openminion` is unavailable.
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    if result.returncode != 0 or not CONFIG_PATH.exists():
        exe = Path(sys.executable).parent / "openminion"
        result = subprocess.run(
            [str(exe), "config", "init", "--provider", init_provider, "--force"],
            capture_output=True, text=True, env=env, timeout=120,
        )
    if not CONFIG_PATH.exists():
        raise RuntimeError(
            "openminion config init did not create agents.json: "
            f"{result.stdout[-500:]} {result.stderr[-500:]}"
        )
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for agent_cfg in data.get("agents", {}).values():
        agent_cfg["provider"] = provider
    _patch_runtime(data)
    _patch_provider_model(data, provider, chosen_model)
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return CONFIG_PATH


def _patch_runtime(data: dict) -> None:
    """FixBrief runtime posture, applied on every ensure_config call.

    - Memory capture off: it adds extra structured-output LLM calls per
      turn (and GBNF grammar requests that crash llama.cpp servers).
      Sessions still persist via storage.
    - Turn budgets raised: local CPU inference (~5 tok/s) needs far
      more than the 300 s default; Agent.run(timeout_seconds=...) does
      not override the brain cap (verified locally).
    """
    runtime = data.setdefault("runtime", {})
    runtime["memory_enabled"] = False
    runtime["memory_dynamic_retrieval_enabled"] = False
    runtime["session_summary_enrichment_enabled"] = False
    runtime["brain_turn_timeout_seconds"] = 2400
    runtime["chat_turn_timeout_seconds"] = 2400.0
    gateway = data.setdefault("gateway", {})
    gateway["api_turn_timeout_seconds"] = 2400


def _patch_provider_model(data: dict, provider: str, model: str) -> None:
    providers = data.setdefault("providers", {})
    entry = providers.setdefault(provider, {})
    entry["model"] = model
    # Local CPU inference needs more headroom than the 60s default.
    if provider == "ollama":
        entry["timeout_seconds"] = 300
        entry.setdefault("base_url", "http://127.0.0.1:11434")
    # Any OpenAI-compatible endpoint (e.g. a local llama.cpp server) can
    # be targeted without code changes:
    #   FIXBRIEF_BASE_URL=http://127.0.0.1:8000/v1 FIXBRIEF_API_KEY=local
    base_url = os.environ.get("FIXBRIEF_BASE_URL")
    if base_url:
        entry["base_url"] = base_url
        entry["timeout_seconds"] = 600
    api_key = os.environ.get("FIXBRIEF_API_KEY")
    if api_key:
        entry["api_key"] = api_key


def active_provider_model() -> tuple[str, str]:
    """Read (provider, model) from the project config, if present."""
    if not CONFIG_PATH.exists():
        return ("unconfigured", "unconfigured")
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    agents = data.get("agents", {})
    agent_cfg = next(iter(agents.values()), {}) if agents else {}
    provider = agent_cfg.get("provider", "unknown")
    model = data.get("providers", {}).get(provider, {}).get("model", "unknown")
    return (provider, model)
