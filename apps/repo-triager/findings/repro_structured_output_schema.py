"""FINDING 2 — `Agent(output_type=Model)` never tells the model the schema.

Expected: the turn asks the model for a reply matching ``output_type``.
Actual:   the request carries the user message only; no schema, no JSON
          instruction.  A hosted model answers in prose, `_coerce_output` then
          raises `AgentOutputValidationError`, and a run that "completed" is
          reported to the caller as a failure.

This is why Repo Triager puts the schema in the task message.

Affected: openminion 0.1.24.  Related upstream report: #853.

Run: python findings/repro_structured_output_schema.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _harness import Harness, banner  # noqa: E402

from pydantic import BaseModel  # noqa: E402


class Triage(BaseModel):
    issue_number: int
    severity: str
    reason: str


def main() -> int:
    banner("FINDING 2 — output_type schema never reaches the model")
    os.environ["SCRIPTED_DUMP"] = "1"
    # The scripted "model" answers in prose, exactly like a hosted model that
    # was never told to answer with JSON.
    scripts = {"schema": {"steps": [{"kind": "text", "content": "This issue looks like an S2 to me."}]}}

    schema_seen_in_any_request = False
    with Harness(scripts=scripts, name="schema") as harness:
        from openminion import Agent

        with Agent(
            runtime=harness.runtime,
            instructions="Classify the issue.",
            output_type=Triage,
            session_id="schema-repro",
        ) as agent:
            try:
                result = agent.run("SCENARIO:schema classify issue 859")
                print(f"turn state: {result.run_state}")
            except Exception as exc:  # noqa: BLE001
                print(f"raised: {type(exc).__name__}: {str(exc)[:160]}")

        for record in harness.requests():
            payload = record.get("payload") or {}
            blob = json.dumps(payload)
            if '"issue_number"' in blob or '"severity"' in blob and '"properties"' in blob:
                schema_seen_in_any_request = True

    print()
    print(f"Triage schema present in any model request: {schema_seen_in_any_request}")
    if not schema_seen_in_any_request:
        print("RESULT: REPRODUCED — the request asks for no particular shape, so the")
        print("        prose reply fails validation after the model call was paid for.")
        print("        Workaround used by Repo Triager: put the JSON schema in the")
        print("        task message (see repo_triager/agent.py: OUTPUT_SCHEMA).")
        return 0
    print("RESULT: not reproduced on this version.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
