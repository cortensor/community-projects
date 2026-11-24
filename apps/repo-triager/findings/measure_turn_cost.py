"""MEASUREMENT — what one triage turn costs on OpenMinion 0.1.24.

A single ``Agent.run`` is not one model call.  The brain orchestrator issues
several structured calls around the action loop (auto fact extraction,
freshness classification, reflection, closure judgment) plus one call per tool
step.  This script prints the measured breakdown so the cost of a batch is a
known quantity rather than a surprise.

Run: python findings/measure_turn_cost.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from _harness import Harness, banner  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from repo_triager.github import load_fixture_snapshot  # noqa: E402
from repo_triager.scripted_demo import scripts_for_issues  # noqa: E402


def main() -> int:
    banner("MEASUREMENT — per-turn model calls")
    snapshot = load_fixture_snapshot(os.path.join(ROOT, "tests", "fixtures", "issues_openminion.json"))
    issue = snapshot.issue(859)
    assert issue is not None
    scripts = scripts_for_issues(snapshot, [issue])

    with Harness(scripts=scripts, name="cost") as harness:
        from repo_triager.agent import TriagerAgent

        agent = TriagerAgent(harness.settings, snapshot, runtime=harness.runtime)
        decision, phase, _context = agent.analyse(
            issue, session_id="cost-repro", scenario="issue-859"
        )
        metadata = phase.metadata

    purposes = metadata.get("llm_call_counts_by_purpose", "{}")
    if isinstance(purposes, str):
        try:
            purposes = json.loads(purposes)
        except json.JSONDecodeError:
            purposes = {}
    print(f"decision          : {decision.severity} {decision.component}")
    print(f"LLM calls         : {metadata.get('llm_calls')}")
    print(f"tool calls        : {metadata.get('tool_calls')}")
    print(f"input tokens      : {metadata.get('total_input_tokens_used')}")
    print(f"output tokens     : {metadata.get('total_output_tokens_used')}")
    print(f"elapsed (ms)      : {metadata.get('elapsed_ms')}")
    print("calls by purpose  :")
    for purpose, count in sorted(purposes.items()):
        if count:
            print(f"    {purpose:22s} {count}")
    print()
    print("Reading: the tool loop is the small part. The fixed per-turn calls")
    print("(afe + freshness + reflect + judge) dominate; a 5-issue batch pays them")
    print("five times over, which is why the CLI keeps batches small and caches")
    print("the issue snapshot locally.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
