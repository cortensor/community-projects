"""FINDING 5 — operator CLIs crash when the uid has no passwd entry.

Expected: `openminion skill ingest` (and `skill admit`, cron/task paths) works in
          a container.
Actual:   the CLI derives the operator id with ``getpass.getuser()``; with no
          ``/etc/passwd`` entry for the current uid that raises
          ``KeyError: 'getpwuid(): uid not found: 1000'``.  The JSON surface
          swallows it into ``{"ok": false, "error": {"code": "UNKNOWN"}}`` and a
          plain ``openminion: ...`` line, so the cause is invisible.

This is the common shape of a CI runner or a distroless/rootless container.

Affected: openminion 0.1.24 — ``openminion/cli/identity/operator.py:9``.

Proposed fix (``findings/patches/operator_id_fallback.patch``): fall back to the
environment or the numeric uid.

Workaround used by Repo Triager: export ``USER`` (getpass reads it first).

Run: python findings/repro_operator_id_getpwuid.py
"""

from __future__ import annotations

import os
import pwd
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from repo_triager.config import RuntimeSession, Settings  # noqa: E402


def _has_passwd_entry() -> bool:
    try:
        pwd.getpwuid(os.getuid())
        return True
    except KeyError:
        return False


def main() -> int:
    print()
    print("=" * 72)
    print("FINDING 5 — operator id derived from getpwuid")
    print("=" * 72)
    print(f"uid {os.getuid()} has a passwd entry: {_has_passwd_entry()}")
    print("getpass.getuser() usable        : ", end="")
    import getpass

    try:
        print(repr(getpass.getuser()))
    except KeyError as exc:
        print(f"KeyError: {exc}")

    settings = Settings(workspace="/tmp/repo-triager-repro-operator")
    settings.ensure_dirs()
    skill = os.path.join(os.path.dirname(__file__), "..", "src", "repo_triager",
                         "skills", "repo-triager-triage", "SKILL.md")
    with RuntimeSession(settings, provider_mode="scripted"):
        env = dict(os.environ)
        env.pop("USER", None)
        env.pop("LOGNAME", None)
        env["OPENAI_COMPATIBLE_API_KEY"] = "repo-triager-local-scripted"
        cmd = [
            sys.executable, "-m", "openminion",
            "--home-root", str(settings.om_home),
            "skill", "ingest", "--name", "repro", "--file", os.path.abspath(skill),
            "--scope", "global",
        ]
        bare = subprocess.run(cmd, env=env, capture_output=True, text=True)

    print()
    print("without USER set:")
    print((bare.stdout or bare.stderr).strip()[:300])
    print()
    if "getpwuid" in (bare.stdout + bare.stderr) and not _has_passwd_entry():
        print("RESULT: REPRODUCED — set USER (or add a passwd entry) and it works;")
        print("        the error text does not name the cause.")
        return 0
    print("RESULT: this host has a passwd entry, so the failure cannot be reproduced here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
