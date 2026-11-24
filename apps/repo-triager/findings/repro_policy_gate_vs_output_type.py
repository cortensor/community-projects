"""FINDING 3 — a denied or paused policy confirmation breaks a structured-output run.

Expected: when the operator refuses `stage_triage`, the caller learns that the
          write was refused by policy.
Actual:   the turn ends with the runtime's refusal text, `_coerce_output` then
          tries to parse that text as the caller's model and raises
          `AgentOutputValidationError`.  The policy outcome is only visible in
          the exception as raw text, and the same happens with `pause` mode.

Consequence for Repo Triager: the write gate runs in its own Agent turn with
``output_type=None`` so a refusal stays a refusal.

Affected: openminion 0.1.24 (related upstream reports: #852, #803).

Run: python findings/repro_policy_gate_vs_output_type.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _harness import Harness, banner  # noqa: E402

from pydantic import BaseModel  # noqa: E402


class Applied(BaseModel):
    applied: bool


def main() -> int:
    banner("FINDING 3 — policy denial vs. structured output")
    written: list[str] = []

    with Harness(scripts={"gate": {"steps": [
        {"kind": "tool", "tool": "write_thing", "args": {"name": "x"}},
        {"kind": "text", "content": "{\"applied\": true}"},
    ]}}, name="gate") as harness:
        from openminion import Agent, tool

        @tool  # bare @tool = local write, unknown reversibility -> confirmation
        def write_thing(name: str) -> str:
            """Write one thing locally."""

            written.append(name)
            return "ok"

        with Agent(
            runtime=harness.runtime,
            instructions="Write the thing.",
            tools=[write_thing],
            output_type=Applied,
            session_id="gate-repro",
        ) as agent:
            try:
                result = agent.run(
                    "SCENARIO:gate write x", approval_callback=lambda *a: False
                )
                print(f"denied run returned: {result.output}")
                print("RESULT: not reproduced on this version.")
                return 1
            except Exception as exc:  # noqa: BLE001
                print(f"raised: {type(exc).__name__}")
                print(f"message: {str(exc).splitlines()[0]}")
                raw = getattr(exc, "raw_text", "")
                print(f"raw reply text: {raw[:120]!r}")

    print()
    print(f"tool executed despite the denial: {bool(written)}")
    assert not written, "the write tool must not run when approval is denied"
    print("RESULT: REPRODUCED — the write was correctly blocked, but the caller")
    print("        receives AgentOutputValidationError instead of a policy result.")
    print("        Workaround: run gated writes without output_type.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
