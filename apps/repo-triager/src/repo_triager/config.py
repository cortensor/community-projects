"""Paths, environment, and OpenMinion runtime bootstrap for Repo Triager."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_REPO = "openminion/openminion"
DEFAULT_LIMIT = 8

#: Provider presets we can bootstrap without asking the operator anything.
PROVIDER_ENV_PRESETS: tuple[tuple[str, str, str], ...] = (
    ("CORTENSOR_API_KEY", "cortensor-portal", "oss-20b"),
    ("OPENAI_API_KEY", "openai", "gpt-4.1-mini"),
    ("GROQ_API_KEY", "groq", "llama-3.3-70b-versatile"),
    ("CEREBRAS_API_KEY", "cerebras", "gpt-oss-120b"),
    ("OPENROUTER_API_KEY", "openrouter", "openai/gpt-4.1-mini"),
    ("ANTHROPIC_API_KEY", "anthropic", "claude-sonnet-5"),
    ("GEMINI_API_KEY", "gemini", "gemini-3.6-flash"),
    ("DEEPSEEK_API_KEY", "deepseek", "deepseek-v4-flash"),
)


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    return Path(raw).expanduser().resolve() if raw else default


@dataclass
class Settings:
    """Every knob the CLI reads, resolved once so tests can override it."""

    repo: str = DEFAULT_REPO
    workspace: Path = field(default_factory=lambda: _env_path("REPO_TRIAGER_HOME", Path.cwd() / "var"))
    om_home: Path | None = None
    provider_mode: str = "auto"  # auto | scripted | configured
    model: str | None = None
    github_token: str = ""
    #: "offline" reads tests/fixtures/issues_openminion.json, "live" calls GitHub.
    source: str = "offline"

    def __post_init__(self) -> None:
        self.workspace = Path(self.workspace).expanduser().resolve()
        if self.om_home is None:
            env_home = os.environ.get("REPO_TRIAGER_OM_HOME", "").strip()
            self.om_home = (
                Path(env_home).expanduser().resolve()
                if env_home
                else self.workspace / "openminion-home"
            )
        else:
            self.om_home = Path(self.om_home).expanduser().resolve()
        if not self.github_token:
            self.github_token = (
                os.environ.get("GITHUB_TOKEN")
                or os.environ.get("GH_TOKEN")
                or ""
            ).strip()

    # -- directories --------------------------------------------------------
    @property
    def data_dir(self) -> Path:
        return self.workspace / "data"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def runs_dir(self) -> Path:
        return self.workspace / "runs"

    @property
    def outbox_dir(self) -> Path:
        return self.workspace / "outbox"

    @property
    def artifacts_dir(self) -> Path:
        return self.workspace / "artifacts"

    def ensure_dirs(self) -> None:
        for path in (
            self.workspace,
            self.data_dir,
            self.cache_dir,
            self.runs_dir,
            self.outbox_dir,
            self.artifacts_dir,
            self.om_home,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @property
    def config_path(self) -> Path:
        assert self.om_home is not None
        return self.om_home / ".openminion" / "agents.json"

    def cache_path(self, repo: str | None = None) -> Path:
        slug = (repo or self.repo).replace("/", "_")
        return self.cache_dir / f"{slug}_issues.json"


def _port_is_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def detect_provider() -> tuple[str, str, dict[str, str]] | None:
    """Return ``(preset, model, env)`` for the first configured credential."""

    base_url = os.environ.get("OPENAI_COMPATIBLE_BASE_URL", "").strip()
    if base_url:
        # Any OpenAI-compatible endpoint (a local server, a gateway, a hosted
        # proxy). The model id comes from REPO_TRIAGER_MODEL.
        return (
            "custom-openai-compatible",
            os.environ.get("REPO_TRIAGER_MODEL", "model-id").strip() or "model-id",
            {"OPENAI_COMPATIBLE_API_KEY": os.environ.get("OPENAI_COMPATIBLE_API_KEY") or "local"},
        )
    for env_name, preset, model in PROVIDER_ENV_PRESETS:
        value = os.environ.get(env_name, "").strip()
        if value:
            return preset, model, {env_name: value}
    if _port_is_open("127.0.0.1", 11434):
        return "ollama", "llama3.1", {}
    return None


class RuntimeBootstrapError(RuntimeError):
    """Raised when no model provider can be configured."""


@dataclass
class RuntimeSession:
    """Owns the OpenMinion home directory for one CLI invocation.

    In ``scripted`` mode it starts the local scripted provider, points
    OpenMinion at it through ``openminion setup``, and makes the run fully
    reproducible without any credential or network access.
    """

    settings: Settings
    provider_mode: str = "auto"
    scripted_scripts: dict | None = None
    _provider: object | None = None
    _request_log: Path | None = None
    patched: dict = field(default_factory=dict)

    def __enter__(self) -> "RuntimeSession":
        settings = self.settings
        settings.ensure_dirs()
        mode = self.provider_mode
        if mode == "auto":
            mode = "scripted" if os.environ.get("REPO_TRIAGER_PROVIDER", "").strip() == "scripted" else "configured"
        if mode == "scripted":
            self._start_scripted_provider()
        if not settings.config_path.exists():
            self._run_setup(mode)
        self._patch_config()
        return self

    def __exit__(self, *exc: object) -> None:
        provider = self._provider
        if provider is not None and hasattr(provider, "__exit__"):
            provider.__exit__(*exc)  # type: ignore[attr-defined]

    # -- scripted provider --------------------------------------------------
    def _start_scripted_provider(self) -> None:
        from repo_triager.scripted_provider import ScriptedProvider

        self._request_log = self.settings.artifacts_dir / "scripted-provider-requests.jsonl"
        provider = ScriptedProvider(
            scripts=self.scripted_scripts or {},
            port=0,
            log_path=self._request_log,
        )
        provider.__enter__()
        self._provider = provider
        # The runtime reads the credential from the environment, so the
        # in-process runtime needs it too (a placeholder, never a real key).
        os.environ["OPENAI_COMPATIBLE_API_KEY"] = "repo-triager-local-scripted"
        assert self.settings.om_home is not None
        self.provider_mode = "scripted"
        self.patched["scripted_base_url"] = provider.base_url  # type: ignore[attr-defined]

    @property
    def base_url(self) -> str | None:
        provider = self._provider
        return getattr(provider, "base_url", None) if provider is not None else None

    @property
    def request_log(self) -> Path | None:
        return self._request_log

    # -- openminion setup ---------------------------------------------------
    def _run_setup(self, mode: str) -> None:
        settings = self.settings
        assert settings.om_home is not None
        env = dict(os.environ)
        env.pop("OPENMINION_HOME", None)
        if not env.get("USER") and not env.get("LOGNAME"):
            env["USER"] = "repo-triager"
            env["LOGNAME"] = "repo-triager"
        if mode == "scripted":
            base_url = self.base_url
            if not base_url:
                raise RuntimeBootstrapError("scripted provider did not start")
            env["OPENAI_COMPATIBLE_API_KEY"] = "repo-triager-local-scripted"
            cmd = [
                sys.executable, "-m", "openminion",
                "--home-root", str(settings.om_home),
                "setup",
                "--provider", "custom-openai-compatible",
                "--base-url", base_url,
                "--model", "scripted-1",
                "--no-chat",
            ]
        else:
            detected = detect_provider()
            if detected is None:
                raise RuntimeBootstrapError(
                    "No model provider is configured. Export a provider key "
                    "(for example CORTENSOR_API_KEY, OPENAI_API_KEY or "
                    "GROQ_API_KEY), run `openminion setup`, or run with "
                    "`--provider scripted` to use the offline scripted model."
                )
            preset, model, extra_env = detected
            env.update(extra_env)
            cmd = [
                sys.executable, "-m", "openminion",
                "--home-root", str(settings.om_home),
                "setup",
                "--provider", preset,
                "--model", settings.model or model,
                "--no-chat",
            ]
            if preset.startswith("custom-"):
                cmd += ["--base-url", os.environ.get("OPENAI_COMPATIBLE_BASE_URL", "")]
        completed = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if completed.returncode != 0 or not settings.config_path.exists():
            raise RuntimeBootstrapError(
                "openminion setup failed: "
                + (completed.stderr or completed.stdout).strip()[-1500:]
            )

    def _patch_config(self) -> None:
        """Apply the runtime settings the setup CLI does not expose."""
        settings = self.settings
        config = json.loads(settings.config_path.read_text(encoding="utf-8"))
        runtime = config.setdefault("runtime", {})
        runtime.update(
            {
                "process_mode": "single-process",
                "daemon_auto_start": False,
                "log_level": os.environ.get("REPO_TRIAGER_LOG_LEVEL", "WARNING"),
                "memory_enabled": True,
                "telemetry_enabled": False,
                "chat_turn_timeout_seconds": 180.0,
                "brain_turn_timeout_seconds": 300,
            }
        )
        config.setdefault("action_policy", {}).update(
            {"allow_read_only_without_prompt": True, "default_action": "require_confirm"}
        )
        settings.config_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if self.provider_mode == "scripted" and self.base_url:
            self._point_at_scripted_provider(self.base_url)

    def _point_at_scripted_provider(self, base_url: str) -> None:
        """Repoint every configured model connection at the live scripted port.

        The provider listens on an ephemeral port, so a config written by an
        earlier run would otherwise point at a dead URL.
        """
        settings = self.settings
        config = json.loads(settings.config_path.read_text(encoding="utf-8"))
        providers = config.setdefault("providers", {})
        openai = providers.setdefault("openai", {})
        openai["base_url"] = base_url
        openai["model"] = "scripted-1"
        openai["api_key_env"] = "OPENAI_COMPATIBLE_API_KEY"
        openai["api_key"] = ""
        for agent in (config.get("agents") or {}).values():
            for connection in (agent.get("model_connections") or {}).values():
                overrides = connection.setdefault("provider_config_overrides", {})
                overrides["base_url"] = base_url
                connection["models"] = ["scripted-1"]
            if agent.get("provider") == "openai":
                agent["default_model"] = "scripted-1"
        settings.config_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # -- convenience --------------------------------------------------------
    def run_cli(self, *args: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
        assert self.settings.om_home is not None
        cmd = [
            sys.executable, "-m", "openminion",
            "--home-root", str(self.settings.om_home),
            *args,
        ]
        env = dict(os.environ)
        env.pop("OPENMINION_HOME", None)
        # openminion 0.1.24 calls getpass.getuser() for the operator id; in a
        # container whose uid has no passwd entry that raises KeyError.  USER is
        # the documented, portable input getpass reads first.
        if not env.get("USER") and not env.get("LOGNAME"):
            env["USER"] = "repo-triager"
            env["LOGNAME"] = "repo-triager"
        if self.provider_mode == "scripted":
            env["OPENAI_COMPATIBLE_API_KEY"] = "repo-triager-local-scripted"
        return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)


def find_fixture(path: Path | None = None) -> Path:
    """Locate the bundled offline issue snapshot."""

    if path is not None:
        return Path(path)
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "tests" / "fixtures" / "issues_openminion.json",
        Path.cwd() / "tests" / "fixtures" / "issues_openminion.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("issues_openminion.json fixture not found")


def which_openminion() -> str | None:
    return shutil.which("openminion")
