"""Reproducible regression tests documenting real OpenMinion 0.1.24 findings.

These tests intentionally assert the CURRENT buggy behavior in openminion 0.1.24
so reviewers can deterministically reproduce every finding reported for
Cortensor Hackathon #5.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from openminion import Agent, AgentOutputValidationError, subagent, tool

from conftest import (
    LocalOpenAIServer,
    make_text_reply,
    make_tool_call_reply,
    write_openminion_config,
)


class _StatusSummaryModel(BaseModel):
    status: str
    summary: str


@tool(name="repro_read_tool", min_scope="READ_ONLY", idempotent=True)
def _repro_read_tool(target: str) -> str:
    return f"checked:{target}"


@tool(name="repro_write_tool")
def _repro_write_tool(tag: str) -> str:
    return f"wrote:{tag}"


def test_finding_1_status_summary_json_misclassified_as_raw_tool_markup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finding #1 (openminion/modules/brain/loop/tools/postprocess/rules.py:117-135):

    A valid Pydantic JSON answer containing both ``status`` and ``summary``
    after a tool call is misclassified by ``_looks_like_unexecutable_tool_payload_text``
    as raw tool markup, discarded, and replaced with an evidence-closeout fallback.
    """

    om_root = tmp_path / "f1"
    monkeypatch.setenv("OPENMINION_HOME", str(om_root))
    monkeypatch.setenv("OPENMINION_DATA_ROOT", str(om_root / ".openminion"))

    called = {"read": False}

    def route(body: dict[str, Any], _idx: int) -> dict[str, Any]:
        tools = [t["function"]["name"] for t in body.get("tools", []) if "function" in t]
        if tools == ["submit_output"]:
            return make_text_reply("{}")
        if "repro_read_tool" in tools and not called["read"]:
            called["read"] = True
            return make_tool_call_reply("c1", "repro_read_tool", {"target": "demo"})
        return make_text_reply(json.dumps({"status": "ready", "summary": "All green"}))

    with LocalOpenAIServer(route) as srv:
        cfg_path = write_openminion_config(om_root, openai_base_url=srv.base_url)
        with Agent(
            config_path=str(cfg_path),
            agent_id="auditor",
            tools=[_repro_read_tool],
            forced_tools=["repro_read_tool"],
            output_type=_StatusSummaryModel,
        ) as agent:
            with pytest.raises(AgentOutputValidationError) as exc_info:
                agent.run("Check demo and return JSON with status and summary.")

    assert "emitted raw tool markup after successful tool results" in exc_info.value.raw_text


def test_finding_2_output_type_crashes_on_policy_confirmation_pause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finding #2 (openminion/api/agent.py:370):

    When ``output_type`` is a Pydantic model and a write tool triggers the
    documented pause-and-resume confirmation flow (no ``approval_callback``),
    ``Agent._run_once`` tries to coerce the confirmation prompt into ``output_type``
    and raises ``AgentOutputValidationError``, losing ``result.thread_id``.
    """

    om_root = tmp_path / "f2"
    monkeypatch.setenv("OPENMINION_HOME", str(om_root))
    monkeypatch.setenv("OPENMINION_DATA_ROOT", str(om_root / ".openminion"))

    def route(body: dict[str, Any], _idx: int) -> dict[str, Any]:
        tools = [t["function"]["name"] for t in body.get("tools", []) if "function" in t]
        if tools == ["submit_output"]:
            return make_text_reply("{}")
        return make_tool_call_reply("c_w", "repro_write_tool", {"tag": "v1.0.0"})

    with LocalOpenAIServer(route) as srv:
        cfg_path = write_openminion_config(om_root, openai_base_url=srv.base_url)
        with Agent(
            config_path=str(cfg_path),
            agent_id="auditor",
            tools=[_repro_write_tool],
            forced_tools=["repro_write_tool"],
            output_type=_StatusSummaryModel,
        ) as agent:
            with pytest.raises(AgentOutputValidationError) as exc_info:
                agent.run("Tag v1.0.0")

    assert "Policy confirmation required." in exc_info.value.raw_text


def test_finding_3_subagent_drops_parent_agent_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finding #3 (openminion/api/handoff.py:299-307):

    ``subagent(parent, ...)`` omits ``agent_id=parent.agent_id``, so a child
    created from a non-default agent profile silently runs on ``default_agent``.
    """

    om_root = tmp_path / "f3"
    monkeypatch.setenv("OPENMINION_HOME", str(om_root))
    monkeypatch.setenv("OPENMINION_DATA_ROOT", str(om_root / ".openminion"))

    with LocalOpenAIServer(lambda _b, _i: make_text_reply("from-auditor")) as srv:
        cfg_path = write_openminion_config(
            om_root,
            openai_base_url=srv.base_url,
            default_agent="echo_default",
        )
        with Agent(config_path=str(cfg_path), agent_id="auditor", name="lead") as parent:
            child = subagent(parent, name="helper", instructions="Help.")
            assert parent.agent_id == "auditor"
            assert child.agent_id is None  # Bug: parent.agent_id was dropped
            res = child.run("ping")
            assert res.text.startswith("echo_default:")
            assert len(srv.requests) == 0


def test_finding_4_missing_default_channel_fails_inbound_authenticity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finding #4 (openminion/base/config/core.py:124 & parser/profiles.py:77):

    Omitting ``default_channel`` in an agent profile (as in README.md:189-198)
    leaves ``default_channel=""`` and fails at turn time with ``invalid_channel``.
    """

    om_root = tmp_path / "f4"
    monkeypatch.setenv("OPENMINION_HOME", str(om_root))
    monkeypatch.setenv("OPENMINION_DATA_ROOT", str(om_root / ".openminion"))

    with LocalOpenAIServer(lambda _b, _i: make_text_reply("ok")) as srv:
        cfg_path = write_openminion_config(
            om_root,
            openai_base_url=srv.base_url,
            extra_agents={
                "minimal_readme_agent": {
                    "provider": "openai",
                    "action_policy": {"mode": "bypass"},
                }
            },
        )
        with Agent(config_path=str(cfg_path), agent_id="minimal_readme_agent") as agent:
            with pytest.raises(RuntimeError, match="reason=invalid_channel"):
                agent.run("hello")
