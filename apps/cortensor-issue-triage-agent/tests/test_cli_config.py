"""Config presets + proxy-env fix + CLI surface (no network, no model)."""

import os

import pytest
from typer.testing import CliRunner

from issue_triage.cli import app
from issue_triage.config import fix_proxy_env, resolve_provider

runner = CliRunner()


def test_fix_proxy_env_strips_ipv6_loopback(monkeypatch):
    monkeypatch.setenv(
        "NO_PROXY",
        "localhost,127.0.0.1,::1,[::1],198.19.0.1,fd8b:4f84:7d32:99::1,"
        "[fd8b:4f84:7d32:99::1]",
    )
    fix_proxy_env()
    assert os.environ["NO_PROXY"] == "localhost,127.0.0.1,198.19.0.1"


def test_fix_proxy_env_leaves_clean_value(monkeypatch):
    monkeypatch.setenv("NO_PROXY", "localhost,127.0.0.1")
    fix_proxy_env()
    assert os.environ["NO_PROXY"] == "localhost,127.0.0.1"


def test_default_preset_is_pollinations(monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = resolve_provider("openai-compatible")
    assert settings.base_url == "https://text.pollinations.ai/openai/v1"
    assert settings.model == "openai"


def test_unknown_preset_rejected():
    with pytest.raises(ValueError, match="unknown preset"):
        resolve_provider("nope")


def test_portal_preset_without_url_refuses(monkeypatch):
    monkeypatch.delenv("CORTENSOR_PORTAL_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="CORTENSOR_PORTAL_BASE_URL"):
        resolve_provider("cortensor-portal")


def test_router_preset_without_url_refuses(monkeypatch):
    monkeypatch.delenv("CORTENSOR_ROUTER_BASE_URL", raising=False)
    with pytest.raises(ValueError, match="CORTENSOR_ROUTER_BASE_URL"):
        resolve_provider("cortensor-router")


def test_cli_help_lists_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("triage", "probe", "eval", "approve"):
        assert cmd in result.output


def test_cli_triage_help():
    result = runner.invoke(app, ["triage", "--help"])
    assert result.exit_code == 0
    assert "--issue" in result.output
    assert "--issue-url" in result.output
    assert "--limit" in result.output


def test_cli_probe_help_lists_probes():
    result = runner.invoke(app, ["probe", "--help"])
    assert result.exit_code == 0
    assert "--probe" in result.output


def test_cli_approve_requires_yes_or_no():
    result = runner.invoke(app, ["approve", "--snapshot", "x"])
    assert result.exit_code != 0
    assert "exactly one" in result.output


def test_cli_approve_both_flags_rejected():
    result = runner.invoke(app, ["approve", "--snapshot", "x", "--yes", "--no"])
    assert result.exit_code != 0


def test_cli_triage_without_args_errors():
    result = runner.invoke(app, ["triage"])
    assert result.exit_code != 0


def test_cli_unknown_probe_rejected():
    result = runner.invoke(app, ["probe", "--probe", "not-a-probe"])
    assert result.exit_code != 0
    assert "unknown probe" in result.output
