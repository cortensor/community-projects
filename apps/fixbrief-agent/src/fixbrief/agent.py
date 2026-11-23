"""OpenMinion SDK wiring for FixBrief.

Design rule (learned from other Hackathon #5 builders and verified
locally): **the model never fetches anything**. Deterministic Python
tools collect and structure facts; the model only reasons over them and
returns a schema-validated brief. A write tool exists solely to exercise
OpenMinion's approval gate — it is denied unless the operator passes
``--yes``.

Building blocks exercised here:
- run-scoped decorated tools (``@tool`` with READ_ONLY metadata + one
  bare write tool)
- ``forced_tools`` for a verifiable first tool call
- typed output (``output_type=RepairBrief``) with
  ``AgentOutputValidationError`` handling
- durable sessions (``session_id`` + follow-up turn in the same session)
- approval callback (``approval_callback(tool_name, args, approval_id)``)
- provider / turn-timeout failures (``ProviderError``,
  ``TurnTimeoutError``) mapped to stable CLI exit codes
- run receipts (``AgentRunResult`` stats/metadata) persisted as JSON
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from openminion import (
    Agent,
    AgentOutputValidationError,
    ProviderError,
    TurnTimeoutError,
    __version__ as OPENMINION_VERSION,
    tool,
)

from . import config as cfg
from .facts import extract_facts
from .glossary import lookup as glossary_lookup
from .models import Language, RepairBrief, SourceRef
from .render import render_markdown
from .sources import fetch_url, load_sample
from .store import save_brief

OUTPUTS_DIR = Path("outputs")

_SCHEMA_JSON = json.dumps(RepairBrief.model_json_schema(), separators=(",", ":"))

INSTRUCTIONS = (
    "You are FixBrief, a phone-repair brief writer. "
    "First call get_source_facts for each listed source to collect facts. "
    "Use lookup_term for exact repair terminology when writing in Spanish, "
    "Portuguese, or Arabic. Then return ONLY a JSON object matching this "
    f"exact JSON Schema: {_SCHEMA_JSON} "
    "Ground every cause and step in the tool facts; do not invent "
    "procedures, URLs, or sources that are not supported by the facts. "
    "Write the brief in the requested language. "
    "IMPORTANT: Never call save_brief_markdown unless the user explicitly "
    "asks you to save a file. Your final message must be the JSON object "
    "itself, with no extra text before or after it."
)


class BriefError(RuntimeError):
    """Model-path failure with a stable CLI exit code."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass
class BriefRun:
    brief: RepairBrief
    receipt: dict
    brief_id: int | None


# ---------------------------------------------------------------- tools


@tool(min_scope="READ_ONLY", idempotent=True)
def get_source_facts(kind: str, locator: str) -> str:
    """Collect structured repair facts from one source.

    kind is 'sample' (bundled offline note filename) or 'url' (public
    http/https URL). Returns JSON with the source title and extracted
    facts (causes, steps, tools, warnings).
    """
    if kind == "sample":
        text = load_sample(locator)
        title = Path(locator).stem.replace("-", " ").title()
        ref = SourceRef(title=title, locator=locator, kind="offline-sample")
    elif kind == "url":
        text = fetch_url(locator)
        ref = SourceRef(title=locator, locator=locator, kind="live-url")
    else:
        raise ValueError(f"kind must be 'sample' or 'url', got {kind!r}")
    facts = extract_facts(text)
    return json.dumps(
        {"source": ref.model_dump(), "facts": facts.model_dump()},
        ensure_ascii=False,
    )


@tool(min_scope="READ_ONLY", idempotent=True)
def lookup_term(term: str, lang: str) -> str:
    """Look up an English repair term in the EN/ES/PT/AR glossary."""
    try:
        language = Language(lang.lower())
    except ValueError:
        return f"unsupported language {lang!r}; use en, es, pt, or ar"
    result = glossary_lookup(term, language)
    return result if result is not None else f"term not in glossary: {term}"


@tool
def save_brief_markdown(filename: str, markdown: str) -> str:
    """Write a brief Markdown file under outputs/ (requires approval)."""
    safe_name = Path(filename).name
    if not safe_name.endswith(".md"):
        safe_name += ".md"
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUTS_DIR / safe_name
    path.write_text(markdown, encoding="utf-8")
    return f"saved {path}"


TOOLS = [get_source_facts, lookup_term, save_brief_markdown]


# ------------------------------------------------------------ agent runs


def _approval_factory(auto_approve_writes: bool, log: list[str]):
    def _callback(tool_name: str, args: dict, approval_id: str) -> bool:
        allowed = bool(auto_approve_writes and tool_name == "save_brief_markdown")
        log.append(
            f"approval tool={tool_name} id={approval_id} -> "
            f"{'allow' if allowed else 'deny'}"
        )
        return allowed

    return _callback


def run_model_brief(
    device: str,
    symptom: str,
    sources: list[tuple[str, str]],
    language: Language = Language.EN,
    provider: str = "ollama",
    model: str | None = None,
    session_id: str = "fixbrief-session",
    auto_approve_writes: bool = False,
    timeout_seconds: float = 2400.0,
    persist: bool = True,
) -> BriefRun:
    """Run one model-backed brief turn through the OpenMinion Agent."""
    cfg.normalize_no_proxy()
    config_path = cfg.ensure_config(provider, model)
    active_provider, active_model = cfg.active_provider_model()
    source_lines = "\n".join(f"- kind={k} locator={v}" for k, v in sources)
    prompt = (
        f"Device: {device}\nSymptom: {symptom}\nLanguage: {language.value}\n"
        f"Sources:\n{source_lines}\n"
        "Collect facts with get_source_facts for every source, then return "
        "the RepairBrief JSON."
    )
    approval_log: list[str] = []

    def _attempt(message: str):
        with Agent(
            instructions=INSTRUCTIONS,
            output_type=RepairBrief,
            tools=TOOLS,
            forced_tools=["get_source_facts"],
            config_path=str(config_path),
            session_id=session_id,
        ) as agent:
            return agent.run(
                message,
                timeout_seconds=timeout_seconds,
                approval_callback=_approval_factory(auto_approve_writes, approval_log),
            )

    try:
        try:
            result = _attempt(prompt)
        except AgentOutputValidationError:
            # One corrective retry: weak local models often answer in
            # prose first. The retry names the failure explicitly.
            result = _attempt(
                prompt
                + "\n\nYour previous reply was not valid JSON for the "
                "RepairBrief schema. Reply again with ONLY the JSON "
                "object — no prose, no markdown fences, no invented URLs."
            )
    except ProviderError as exc:
        raise BriefError(
            f"provider failed [{exc.code}]: {exc.message}", exit_code=1
        ) from exc
    except TurnTimeoutError as exc:
        raise BriefError(f"turn timed out: {exc}", exit_code=3) from exc
    except AgentOutputValidationError as exc:
        raise BriefError(
            f"model output did not validate: {exc.raw_text[:400]!r}",
            exit_code=2,
        ) from exc

    brief: RepairBrief = result.output
    brief.generated_by = f"openminion:{active_provider}/{active_model}"
    # Sources are ground truth from the request, never model-invented
    # (a 1.5B model hallucinated an example.com URL in testing).
    brief.sources = [
        SourceRef(
            title=Path(v).stem.replace("-", " ").title() if k == "sample" else v,
            locator=v,
            kind="offline-sample" if k == "sample" else "live-url",
        )
        for k, v in sources
    ]
    receipt = {
        "openminion_version": OPENMINION_VERSION,
        "provider": active_provider,
        "model": active_model,
        "session_id": result.session_id,
        "run_id": result.run_id,
        "thread_id": result.thread_id,
        "stats": result.stats,
        "approval_log": approval_log,
        "device": device,
        "symptom": symptom,
        "language": language.value,
        "sources": [{"kind": k, "locator": v} for k, v in sources],
    }
    brief_id = save_brief(brief, session_id=result.session_id) if persist else None
    return BriefRun(brief=brief, receipt=receipt, brief_id=brief_id)


def run_followup(
    session_id: str,
    message: str,
    provider: str = "ollama",
    model: str | None = None,
    timeout_seconds: float = 2400.0,
    auto_approve_writes: bool = False,
) -> tuple[str, dict]:
    """Continue an existing session with a plain-text follow-up turn."""
    cfg.normalize_no_proxy()
    config_path = cfg.ensure_config(provider, model)
    active_provider, active_model = cfg.active_provider_model()
    approval_log: list[str] = []
    try:
        with Agent(
            instructions=INSTRUCTIONS,
            tools=TOOLS,
            config_path=str(config_path),
            session_id=session_id,
        ) as agent:
            result = agent.run(
                message,
                timeout_seconds=timeout_seconds,
                approval_callback=_approval_factory(
                    auto_approve_writes, approval_log
                ),
            )
    except ProviderError as exc:
        raise BriefError(
            f"provider failed [{exc.code}]: {exc.message}", exit_code=1
        ) from exc
    except TurnTimeoutError as exc:
        raise BriefError(f"turn timed out: {exc}", exit_code=3) from exc
    receipt = {
        "openminion_version": OPENMINION_VERSION,
        "provider": active_provider,
        "model": active_model,
        "session_id": result.session_id,
        "run_id": result.run_id,
        "thread_id": result.thread_id,
        "stats": result.stats,
        "followup": True,
    }
    return result.text, receipt


def write_receipt(receipt: dict, path: Path | None = None) -> Path:
    target = path or (OUTPUTS_DIR / "live_model_run_receipt.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return target


def brief_markdown(brief: RepairBrief) -> str:
    return render_markdown(brief)
