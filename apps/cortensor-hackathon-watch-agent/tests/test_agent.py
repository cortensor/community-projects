"""SDK wiring tests — offline constructs only, zero model cost."""

import tempfile
from pathlib import Path

import pytest

from hackathon_watch.agent import (
    build_classifier_agent, build_isolated_runtime, make_handoff,
    make_lookup_tool, make_subagent_classifier)
from hackathon_watch.config import resolve_provider
from hackathon_watch.models import HackathonEntry, SuitabilityVerdict


@pytest.fixture
def provider():
    return resolve_provider("openai-compatible")


def test_runtime_builds_with_isolated_roots(provider):
    with tempfile.TemporaryDirectory() as tmp:
        rt = build_isolated_runtime(provider, Path(tmp))
        try:
            # data_root is created eagerly with its SQLite stores;
            # home_root is created lazily by the runtime.
            assert (Path(tmp) / "data").exists()
            assert rt is not None
        finally:
            rt.close()


def test_runtime_rejects_empty_agents_config(provider):
    from openminion import APIRuntime
    from openminion.base.config import OpenMinionConfig
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(Exception, match="agents is empty"):
            APIRuntime.from_config(config=OpenMinionConfig(),
                                   home_root=Path(tmp) / "home",
                                   data_root=Path(tmp) / "data")


def test_lookup_tool_is_read_only():
    known = {"k": HackathonEntry(name="Stub Hack",
                                 url="https://example.test/x",
                                 source="devfolio")}
    lookup = make_lookup_tool(known)
    assert lookup.tool_decl.name == "lookup_known_hackathon"
    assert lookup.tool_decl.min_scope == "READ_ONLY"
    assert lookup.tool_decl.dangerous is False


def test_classifier_agent_constructs_with_forced_tool(provider):
    with tempfile.TemporaryDirectory() as tmp:
        rt = build_isolated_runtime(provider, Path(tmp))
        try:
            agent = build_classifier_agent(rt, {}, provider)
            assert agent.name == "watch"
            assert agent.output_type is SuitabilityVerdict
        finally:
            rt.close()


def test_subagent_is_isolated(provider):
    with tempfile.TemporaryDirectory() as tmp:
        rt = build_isolated_runtime(provider, Path(tmp))
        try:
            parent = build_classifier_agent(rt, {}, provider)
            child = make_subagent_classifier(parent, timeout_seconds=60)
            assert child.name == "classifier"
            assert child.subagent_context.timeout_seconds == 60
            assert child.subagent_context.parent_transcript_inherited is False
        finally:
            rt.close()


def test_handoff_resolves_name(provider):
    from openminion import Agent
    with tempfile.TemporaryDirectory() as tmp:
        rt = build_isolated_runtime(provider, Path(tmp))
        try:
            specialist = Agent(instructions="Check deadlines.",
                               name="deadline_checker", runtime=rt)
            handoff = make_handoff(None, specialist)
            assert handoff.resolved_name() == "transfer_to_deadline_checker"
        finally:
            rt.close()


def test_memory_bundle_round_trip_offline():
    from openminion.modules.memory.portability import (
        export_bundle, import_bundle, load_bundle, save_bundle)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "b.json"
        bundle = export_bundle(
            [{"kind": "hackathon", "id": "k1", "name": "Stub Hack"}],
            metadata={"agent": "hackathon-watch"})
        save_bundle(bundle, str(path))
        info = import_bundle(load_bundle(str(path)), trust_mode="direct")
        assert info["item_count"] == 1
        with pytest.raises(Exception, match="trust_mode"):
            import_bundle(load_bundle(str(path)), trust_mode="bogus")
