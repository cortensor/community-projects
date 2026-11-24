"""FINDING 6 — `memory.search` returns "[TRUNCATED]" instead of the stored content.

Expected: a search result carries the record content so the agent can use it.
Actual:   every value of a structured ``content`` dict arrives as the literal
          string "[TRUNCATED]", so the agent knows a record exists but not what
          it says.  Repo Triager therefore stores decisions as a compact string
          summary instead of a dict.

Affected: openminion 0.1.24 (memory tool rendering).

Run: python findings/repro_memory_search_truncation.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _harness import Harness, banner  # noqa: E402

KEY = "triage:repro:859"


def main() -> int:
    banner("FINDING 6 — memory.search truncates structured content")
    scripts = {
        "write": {
            "steps": [
                {
                    "kind": "tool",
                    "tool": "memory_write",
                    "args": {
                        "record_type": "decision",
                        "key": KEY,
                        "title": "Triage decision for #859",
                        "content": {
                            "severity": "S2",
                            "component": "area:tools",
                            "labels": ["bug", "area:tools"],
                        },
                        "tags": ["repo-triager"],
                    },
                },
                {"kind": "text", "content": "stored"},
            ]
        },
        "search": {
            "steps": [
                {
                    "kind": "tool",
                    "tool": "memory_search",
                    "args": {"query": "triage decision severity"},
                },
                {"kind": "text", "content": "searched"},
            ]
        },
    }

    with Harness(scripts=scripts, name="memory") as harness:
        from openminion import Agent

        with Agent(
            runtime=harness.runtime,
            instructions="Store the decision.",
            tools=["memory.write"],
            forced_tools=["memory.write"],
            session_id="memory-repro",
        ) as writer:
            writer.run(
                "SCENARIO:write store it",
                approval_callback=lambda name, args, approval_id: name == "memory.write",
            )

        with Agent(
            runtime=harness.runtime,
            instructions="Search memory.",
            tools=["memory.search"],
            forced_tools=["memory.search"],
            session_id="memory-repro",
        ) as reader:
            reader.run("SCENARIO:search look it up")

        results = [
            record["last_tool"]
            for record in harness.requests()
            if record.get("last_tool") and "memory search" in record["last_tool"]
        ]

    print(f"memory.search calls captured: {len(results)}")
    if not results:
        print("RESULT: no search result captured; run again with SCRIPTED_DUMP unset.")
        return 1
    payload = results[-1]
    print(payload[:700])
    truncated = "[TRUNCATED]" in payload
    print()
    if truncated:
        print("RESULT: REPRODUCED — the record's values arrive as [TRUNCATED];")
        print("        only the record id, key, and metadata remain usable.")
        return 0
    print("RESULT: not reproduced on this version.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
