"""Regression tests reproducing real OpenMinion 0.1.24 rough edges documented in OPENMINION_FEEDBACK.md."""

import json
from pathlib import Path

import pytest
from openminion import APIRuntime, Agent, Handoff, OpenMinionConfig, subagent
from openminion.base.config.base import ConfigError
from openminion.base.config.io import load_config
from openminion.modules.skill.errors import SkillError
from openminion.modules.skill.interfaces import SkillIngestAuthority
from openminion.modules.skill.runtime.skill import Skill
from openminion.modules.task.surface import TaskSurface

from novatriage_minion.local_model import (
    NovaTriageLocalModelServer,
    build_openminion_config_file,
)
from novatriage_minion.tools import analyze_solidity_contract


def test_finding_1_load_config_rejects_yaml_despite_pyyaml_dependency(tmp_path: Path) -> None:
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text("agents:\n  default:\n    provider: echo\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Invalid JSON config"):
        load_config(str(yaml_path))


def test_finding_2_empty_default_channel_fails_even_in_warn_mode(tmp_path: Path) -> None:
    cfg = OpenMinionConfig().to_dict()
    cfg["agents"]["default"] = {"provider": "echo", "model": "echo"}
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    rt = APIRuntime.from_config_path(
        str(cfg_path),
        home_root=str(tmp_path / "h"),
        data_root=str(tmp_path / "d"),
    )
    try:
        agent = Agent(runtime=rt, instructions="Test")
        with pytest.raises(RuntimeError, match="inbound authenticity denied \\(reason=invalid_channel, mode=warn\\)"):
            agent.run("hello")
    finally:
        rt.close()


def test_finding_3_subagent_in_handoff_deadlocks_shared_runtime(tmp_path: Path) -> None:
    with NovaTriageLocalModelServer.start() as srv:
        cfg_path = build_openminion_config_file(
            tmp_path / "cfg.json",
            provider="local",
            local_base_url=srv.base_url,
        )
        rt = APIRuntime.from_config_path(
            str(cfg_path),
            home_root=str(tmp_path / "h"),
            data_root=str(tmp_path / "d"),
        )
        try:
            parent = Agent(runtime=rt, name="parent", instructions="Parent")
            child = subagent(
                parent,
                name="solidity_auditor_minion",
                tools=[analyze_solidity_contract],
                instructions="Audit",
            )
            assert child._runtime is rt  # subagent() forces parent's shared runtime
            coord = Agent(
                runtime=rt,
                name="coord",
                handoffs=[
                    Handoff(
                        target=child,
                        name="transfer_to_solidity_auditor_minion",
                    )
                ],
                instructions="Coord",
            )
            seen_tool_errors: list[str] = []
            orig_handle = srv.server.RequestHandlerClass
            from novatriage_minion import local_model

            orig_fn = local_model._handle_chat_completion

            def capture_err(body: dict) -> dict:
                for msg in body.get("messages", []):
                    if msg.get("role") == "tool" and "Tool execution failed" in str(msg.get("content", "")):
                        seen_tool_errors.append(str(msg["content"]))
                return orig_fn(body)

            local_model._handle_chat_completion = capture_err
            try:
                coord.run(
                    "Audit contract_path=samples/VulnerableVault.sol",
                    approval_callback=lambda *a: True,
                )
            finally:
                local_model._handle_chat_completion = orig_fn

            assert any("RuntimeError" in err and "EXEC_ERROR" in err for err in seen_tool_errors)
        finally:
            rt.close()


def test_finding_4_skill_render_snippet_rejects_undocumented_purpose(tmp_path: Path) -> None:
    ctl = Skill({"ingest_enabled": True}, home_root=tmp_path)
    try:
        auth = SkillIngestAuthority.local_operator(
            surface="test", principal_id="op", source_kind="local"
        )
        skill_id, vhash, _ = ctl.ingest_text(
            name="demo-skill",
            markdown="# Summary\nDemo\n\n# Procedure\n1. Step one\n",
            authority=auth,
        )
        with pytest.raises(SkillError, match="purpose must be one of: plan, respond, act, verify"):
            ctl.render_snippet(skill_id, vhash, "execution", 200)
    finally:
        ctl.close()


def test_finding_5_task_surface_list_tasks_param_mismatch(tmp_path: Path) -> None:
    import inspect

    sig = inspect.signature(TaskSurface.list_tasks)
    assert "runs_limit" in sig.parameters
    assert "limit" not in sig.parameters
