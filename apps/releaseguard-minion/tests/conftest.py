"""Shared fixtures for ReleaseGuard Minion integration & finding-repro tests."""

from __future__ import annotations

import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

import pytest


class LocalOpenAIServer:
    """Loopback OpenAI-compatible HTTP server for deterministic OpenMinion tests.

    OpenMinion connects to this server through its real ``openai`` provider
    transport (httpx + llmctl), exercising the full runtime stack without
    paid API calls or local GPU weights.
    """

    def __init__(self, handler: Callable[[dict[str, Any], int], dict[str, Any]]) -> None:
        self._handler = handler
        self.requests: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        outer = self

        class _HTTPHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                body = json.loads(raw)
                with outer._lock:
                    idx = len(outer.requests)
                    outer.requests.append(body)
                    reply = outer._handler(body, idx)
                encoded = json.dumps(reply).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _HTTPHandler)
        self.base_url = f"http://127.0.0.1:{self._server.server_address[1]}/v1"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def __enter__(self) -> LocalOpenAIServer:
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._server.shutdown()
        self._server.server_close()


def make_tool_call_reply(
    call_id: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-{call_id}",
        "object": "chat.completion",
        "model": "local-test-model",
        "choices": [
            {
                "index": 0,
                "finish_reason": "tool_calls",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(arguments),
                            },
                        }
                    ],
                },
            }
        ],
        "usage": {"prompt_tokens": 25, "completion_tokens": 12, "total_tokens": 37},
    }


def make_text_reply(content: str) -> dict[str, Any]:
    return {
        "id": "chatcmpl-text",
        "object": "chat.completion",
        "model": "local-test-model",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content},
            }
        ],
        "usage": {"prompt_tokens": 25, "completion_tokens": 18, "total_tokens": 43},
    }


def write_openminion_config(
    root: Path,
    *,
    openai_base_url: str,
    default_agent: str = "echo_default",
    extra_agents: dict[str, Any] | None = None,
) -> Path:
    """Create an isolated OpenMinion agents.json with SQLite state under ``root``."""

    cfg_path = root / ".openminion" / "agents.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    agents: dict[str, Any] = {
        "echo_default": {
            "name": "echo_default",
            "provider": "echo",
            "default_channel": "console",
            "system_prompt": "Default echo profile.",
        },
        "auditor": {
            "name": "auditor",
            "provider": "openai",
            "default_channel": "console",
            "system_prompt": "Repository release auditor.",
        },
    }
    if extra_agents:
        agents.update(extra_agents)

    cfg = {
        "default_agent": default_agent,
        "enabled_channels": ["console"],
        "action_policy": {
            "mode": "auto",
            "default_action": "require_confirm",
            "allow_read_only_without_prompt": True,
            "rules": [],
        },
        "agents": agents,
        "providers": {
            "openai": {
                "base_url": openai_base_url,
                "api_key": "local-test-token",
                "model": "local-test-model",
                "timeout_seconds": 30,
            }
        },
        "runtime": {
            "demo_mode": False,
        },
        "storage": {
            "backend": "sqlite",
            "path": str(root / ".openminion" / "state" / "openminion.db"),
        },
    }
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg_path


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a realistic sample git repository for release-readiness auditing."""

    repo = tmp_path / "demo-protocol"
    repo.mkdir()
    (repo / "README.md").write_text("# Demo Protocol\n\nRelease-ready repo.\n", encoding="utf-8")
    (repo / "LICENSE").write_text("Apache License 2.0\n", encoding="utf-8")
    (repo / "CHANGELOG.md").write_text("## 0.1.0\n- Initial release\n", encoding="utf-8")
    (repo / "SECURITY.md").write_text("Report issues to security@example.com\n", encoding="utf-8")
    (repo / ".gitignore").write_text(".env\n.venv/\n__pycache__/\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text('[project]\nname = "demo-protocol"\n', encoding="utf-8")
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: CI\non: [push, pull_request]\n", encoding="utf-8")
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_core.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (repo / "Makefile").write_text("test:\n\tpytest\n", encoding="utf-8")

    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.email", "ci@example.com"], cwd=str(repo), check=True)
    subprocess.run(["git", "config", "user.name", "CI Bot"], cwd=str(repo), check=True)
    subprocess.run(["git", "add", "."], cwd=str(repo), check=True)
    subprocess.run(["git", "commit", "-q", "-m", "Initial commit"], cwd=str(repo), check=True)
    return repo


@pytest.fixture
def leaky_repo(tmp_path: Path) -> Path:
    """Create a repository with missing LICENSE/CI and an exposed secret + .env."""

    repo = tmp_path / "leaky-repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Leaky Repo\n", encoding="utf-8")
    (repo / ".env").write_text("SECRET_TOKEN=test\n", encoding="utf-8")
    (repo / "config.py").write_text(
        'PRIVATE_KEY = "0x' + ("ab" * 32) + '"\n',
        encoding="utf-8",
    )
    return repo
