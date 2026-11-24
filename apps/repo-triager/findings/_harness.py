"""Shared harness for the reproduction scripts in ``findings/``.

Each script boots a throwaway OpenMinion home plus the scripted provider, so a
reviewer needs no credential and no network:

    python findings/repro_instructions_truncation.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repo_triager.config import RuntimeSession, Settings  # noqa: E402


class Harness:
    """A disposable OpenMinion home wired to the scripted provider."""

    def __init__(self, scripts: dict | None = None, name: str = "repro") -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix=f"om-repro-{name}-"))
        self.settings = Settings(
            repo="openminion/openminion", workspace=self.tmp, provider_mode="scripted"
        )
        self.scripts = scripts or {}
        self.session: RuntimeSession | None = None
        self.runtime = None

    def __enter__(self) -> "Harness":
        self.settings.ensure_dirs()
        os.environ["OPENAI_COMPATIBLE_API_KEY"] = "repo-triager-local-scripted"
        self.session = RuntimeSession(
            self.settings, provider_mode="scripted", scripted_scripts=self.scripts
        ).__enter__()
        from repo_triager.agent import open_runtime

        self.runtime = open_runtime(self.settings)
        return self

    def __exit__(self, *exc: object) -> None:
        if self.runtime is not None:
            self.runtime.close()
        if self.session is not None:
            self.session.__exit__(*exc)

    @property
    def base_url(self) -> str:
        return getattr(self.session, "base_url", "") or ""

    @property
    def log(self) -> Path:
        return self.settings.artifacts_dir / "scripted-provider-requests.jsonl"

    def requests(self) -> list[dict]:
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines() if line]

    def system_messages(self) -> list[str]:
        out: list[str] = []
        for record in self.requests():
            payload = record.get("payload") or {}
            for message in payload.get("messages", []):
                if message.get("role") == "system":
                    out.append(message.get("content") or "")
        return out


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)
