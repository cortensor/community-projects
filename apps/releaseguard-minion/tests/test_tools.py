"""Unit tests for ReleaseGuard Minion's risk-tiered @tool implementations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from release_guard_minion.policy import ReleaseApprovalGate
from release_guard_minion.tools import (
    create_release_tag,
    inspect_ci_and_tests,
    inspect_repo_manifest,
    scan_secret_hygiene,
    write_release_brief,
)


def test_tool_risk_metadata_contracts() -> None:
    """Verify each @tool declares the expected OpenMinion policy risk tier."""

    for read_tool in (inspect_repo_manifest, inspect_ci_and_tests, scan_secret_hygiene):
        assert read_tool.tool_decl.min_scope == "READ_ONLY"
        assert read_tool.tool_decl.idempotent is True
        assert read_tool.tool_decl.dangerous is False

    assert write_release_brief.tool_decl.min_scope is None
    assert write_release_brief.tool_decl.idempotent is True
    assert write_release_brief.tool_decl.dangerous is False

    assert create_release_tag.tool_decl.dangerous is True


def test_inspect_manifest_ci_and_secrets_on_clean_repo(sample_repo: Path) -> None:
    manifest = json.loads(inspect_repo_manifest(str(sample_repo)))
    assert manifest["repo_name"] == "demo-protocol"
    assert all(manifest["docs_present"].values())
    assert "pyproject.toml" in manifest["manifests"]
    assert manifest["is_git_repo"] is True
    assert manifest["dirty_files_count"] == 0

    ci = json.loads(inspect_ci_and_tests(str(sample_repo)))
    assert ci["ci_workflows"] == ["ci.yml"]
    assert ci["test_file_count"] == 1
    assert "Makefile" in ci["automation_files"]

    secrets = json.loads(scan_secret_hygiene(str(sample_repo)))
    assert secrets["clean"] is True
    assert secrets["gitignore_covers_env"] is True
    assert secrets["secret_findings"] == []


def test_scan_secret_hygiene_detects_env_and_private_key(leaky_repo: Path) -> None:
    secrets = json.loads(scan_secret_hygiene(str(leaky_repo)))
    assert secrets["clean"] is False
    assert ".env" in secrets["env_files_present"]
    rules = {item["rule"] for item in secrets["secret_findings"]}
    assert "evm_private_key" in rules


def test_write_release_brief_and_git_tag(sample_repo: Path, tmp_path: Path) -> None:
    brief_path = tmp_path / "out" / "RELEASE_BRIEF.md"
    result = json.loads(write_release_brief(str(brief_path), "# Ready\n"))
    assert Path(result["written_path"]).read_text(encoding="utf-8") == "# Ready\n"

    tag_res = json.loads(create_release_tag(str(sample_repo), "v0.1.0", "First release"))
    assert tag_res["tag_created"] == "v0.1.0"

    with pytest.raises(ValueError, match="Invalid semantic release tag"):
        create_release_tag(str(sample_repo), "bad tag!", "nope")


def test_approval_gate_single_use_and_fail_closed() -> None:
    gate = ReleaseApprovalGate(allow_write_brief=True, allow_release_tag=False)
    assert gate("write_release_brief", {"output_path": "a.md"}, "ap-1") is True
    assert gate("write_release_brief", {"output_path": "b.md"}, "ap-2") is False
    assert gate("create_release_tag", {"tag_name": "v1.0.0"}, "ap-3") is False
    assert gate("unknown.tool", {}, "ap-4") is False
    assert [d.allowed for d in gate.decisions] == [True, False, False, False]
