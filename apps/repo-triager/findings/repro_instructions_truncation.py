"""FINDING 1 — `Agent(instructions=...)` is truncated at roughly 860 characters.

Expected: every rule in `instructions` reaches the model.
Actual:   rules after ~860 characters are dropped without any warning; the turn
          still completes, so the caller never learns that its later rules were
          never seen.

Affected: openminion 0.1.24.  Related upstream report: #811.

Run: python findings/repro_instructions_truncation.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _harness import Harness, banner  # noqa: E402

SENTINEL = "SENTINEL_END_ABCXYZ"
RULE = "Rule {n:02d}: always explain the reasoning for this triage decision in one clear sentence. "


def main() -> int:
    instructions = "".join(RULE.format(n=n) for n in range(1, 31)) + SENTINEL
    banner("FINDING 1 — instructions truncation")
    print(f"instructions sent : {len(instructions)} characters, 30 rules, sentinel at the end")

    scripts = {"instr": {"steps": [{"kind": "text", "content": "done"}]}}
    os.environ["SCRIPTED_DUMP"] = "1"
    with Harness(scripts=scripts, name="instr") as harness:
        from openminion import Agent, tool

        @tool(min_scope="READ_ONLY", idempotent=True)
        def ping() -> str:
            """Return pong."""

            return "pong"

        with Agent(
            runtime=harness.runtime,
            tools=[ping],
            instructions=instructions,
            session_id="instr-repro",
        ) as agent:
            result = agent.run("SCENARIO:instr hello")

        system_text = next(
            (
                text
                for text in harness.system_messages()
                if "Rule 01" in text
            ),
            "",
        )
        rules = re.findall(r"Rule (\d\d):", system_text)
        print(f"turn state        : {result.run_state}")
        print(f"rules that reached the model: {rules}")
        print(f"sentinel reached the model   : {SENTINEL in system_text}")
        print()
        if SENTINEL not in system_text:
            print("RESULT: REPRODUCED — the later rules never reach the model.")
            print(f"        {len(rules)} of 30 rules survived; everything from rule "
                  f"{int(rules[-1]) + 1 if rules else 1:02d} onward was dropped.")
            return 0
        print("RESULT: not reproduced on this version.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
