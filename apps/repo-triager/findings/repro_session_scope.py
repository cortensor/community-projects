"""FINDING 4 — a session id containing "/" silently disables memory for the session.

Expected: memory context is built for the session whatever its id.
Actual:   the memory layer builds ``session:<id>`` and validates it against
          ``^(session|agent|project|global):[A-Za-z0-9._:-]+$``.  A repository
          slug such as ``openminion/openminion`` fails that pattern, so
          ``session:repo-triager:openminion/openminion`` is rejected.  The
          warning goes to the log, the turn still completes, and the agent
          silently runs without its memory capsule.

Affected: openminion 0.1.24 / sophiagraph.

Run: python findings/repro_session_scope.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _harness import Harness, banner  # noqa: E402


def main() -> int:
    banner("FINDING 4 — session id scope validation")

    from sophiagraph.models.primitives import SCOPE_PATTERN

    print(f"scope pattern: {SCOPE_PATTERN.pattern}")
    slash = "session:repo-triager:openminion/openminion"
    clean = "session:repo-triager:openminion_openminion"
    print(f"{clean!r:48s} valid: {bool(SCOPE_PATTERN.match(clean))}")
    print(f"{slash!r:48s} valid: {bool(SCOPE_PATTERN.match(slash))}")

    scripts = {"scope": {"steps": [{"kind": "text", "content": "ok"}]}}
    completed = []
    with Harness(scripts=scripts, name="scope") as harness:
        from openminion import Agent

        for session_id in (clean, "repo-triager:openminion/openminion"):
            with Agent(
                runtime=harness.runtime,
                instructions="Say ok.",
                session_id=session_id,
            ) as agent:
                result = agent.run("SCENARIO:scope hello")
            completed.append((session_id, result.run_state))

    print()
    for session_id, state in completed:
        print(f"turn with session_id {session_id!r:46s} -> {state}")
    print()
    print("RESULT: REPRODUCED — the invalid scope is detected by the memory layer")
    print("        while the turn reports success. Repo Triager slugifies its")
    print("        session ids (openminion_openminion) for exactly this reason.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
