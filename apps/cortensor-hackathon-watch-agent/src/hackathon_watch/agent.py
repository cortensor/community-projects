"""OpenMinion agent wiring for the classifier.

Two roads, one model (see llm_client.py for why the direct road is the
main one):

- Main road: ``DirectClient`` — one HTTP call per classification, paced
  >=45 s on the Pollinations free tier. Used by ``check``.
- SDK road: a real ``Agent`` with a read-only lookup tool, exercised by
  the probe suite and available for a Portal/Router preset where a
  native turn survives (Pollinations 402 kills it — recorded honestly
  in the probe, not hidden).

SDK facts used here (verified in the sibling SPIKE.md):
- No ``create_isolated_runtime`` in 0.1.21; use
  ``APIRuntime.from_config(config, home_root, data_root)``.
- ``OpenMinionConfig`` needs >= 1 ``AgentProfileConfig``.
- ``AgentProfileConfig`` needs ``default_channel="console"`` or the
  gateway rejects the turn with ``invalid_channel`` (even in warn mode).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ProviderSettings
from .models import HackathonEntry, SuitabilityVerdict


def build_isolated_runtime(provider: ProviderSettings, tmp: Path):
    """APIRuntime with isolated home/data roots (no shared state)."""
    from openminion import APIRuntime
    from openminion.base.config import OpenMinionConfig
    from openminion.base.config.core import AgentProfileConfig
    from openminion.base.config.providers import OpenAIProviderConfig

    cfg = OpenMinionConfig(
        agents={"watch": AgentProfileConfig(
            name="watch", provider="openai", default_channel="console")})
    cfg.providers.openai = OpenAIProviderConfig(
        model=provider.model, api_key=provider.api_key,
        base_url=provider.base_url)
    return APIRuntime.from_config(config=cfg, home_root=tmp / "home",
                                  data_root=tmp / "data")


def make_lookup_tool(known: dict[str, HackathonEntry]):
    """A READ_ONLY tool: look up a remembered hackathon by name fragment."""
    from openminion import tool

    @tool(min_scope="READ_ONLY")
    def lookup_known_hackathon(name_fragment: str) -> str:
        """Look up a hackathon already in memory by part of its name."""
        fragment = (name_fragment or "").lower()
        hits = [f"{e.name} | {e.url} | {e.source}"
                for e in known.values() if fragment in e.name.lower()]
        return "\n".join(hits[:5]) if hits else "no match in memory"

    return lookup_known_hackathon


def build_classifier_agent(runtime, known: dict[str, HackathonEntry],
                           provider: ProviderSettings):
    """Agent that classifies one new entry, output typed as SuitabilityVerdict."""
    from openminion import Agent

    lookup = make_lookup_tool(known)
    return Agent(
        instructions=(
            "You judge whether a newly listed hackathon fits one person: "
            "free-only, online-first, non-student adult, direction LLM / "
            "Agent / AI applications / legal AI, resident Singapore/US. "
            "Use lookup_known_hackathon to check whether it is already known. "
            "Answer only with the JSON verdict object."),
        output_type=SuitabilityVerdict,
        model=provider.model,
        tools=[lookup],
        name="watch",
        runtime=runtime,
    )


def classify_via_agent(agent, entry: HackathonEntry,
                       timeout_seconds: int = 280) -> SuitabilityVerdict:
    """One native SDK turn. Raises ProviderError on the 402 wall etc."""
    result = agent.run(
        f"Classify this newly listed hackathon. Name: {entry.name}. "
        f"URL: {entry.url}. Source: {entry.source}. "
        f"Notes: {entry.notes or '-'}.",
        timeout_seconds=timeout_seconds)
    output = result.output
    if isinstance(output, SuitabilityVerdict):
        return output
    if isinstance(output, dict):
        return SuitabilityVerdict.model_validate(output)
    raise ValueError(f"unexpected agent output type: {type(output)!r}")


def make_subagent_classifier(parent, timeout_seconds: int = 120):
    """A delegated classifier running in an isolated subagent context."""
    from openminion import subagent

    return subagent(
        parent,
        instructions=("Classify one hackathon as preliminary / unsure / "
                      "not-suitable with one short reason, per the same "
                      "free-only, online-first, non-student, LLM/Agent rules."),
        name="classifier",
        timeout_seconds=timeout_seconds,
    )


def make_handoff(agent, specialist) -> Any:
    """Handoff to a specialist agent (e.g. a deadline-checking agent)."""
    from openminion import Handoff

    return Handoff(target=specialist)
