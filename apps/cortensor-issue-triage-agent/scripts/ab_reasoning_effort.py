"""A/B test: does reasoning_effort=low trigger the upstream 400 on the draft call?

Run 1 (17:44 UTC) and run 2 of the probe both died on the draft call with a
byte-identical 400 body (same timestamp 17:44:28.306Z) while the identical
call shape worked in the original triage run — the only payload change
since then is reasoning_effort="low". Test the same draft prompt with and
without reasoning_effort.
"""
import json
import os
import sys

os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

from issue_triage.llm_client import DirectClient
from issue_triage.triage import TriageEngine, draft_tool_schema
from issue_triage.models import TriageDraft, TriageVerdict

raw = json.load(open("fixtures/openminion-issue-778.json"))
ctx = TriageEngine.context_from_fixture("openminion/openminion", raw)
verdict = TriageVerdict(
    issue_type="bug", severity="high", component="brain",
    suggested_labels=["bug", "area:brain"], route="needs-maintainer",
    confidence=0.8, rationale="test",
)
engine = TriageEngine.__new__(TriageEngine)
messages = TriageEngine._drafter_messages(engine, ctx, verdict)

for label, effort in (("A: no reasoning_effort", None), ("B: reasoning_effort=low", "low")):
    client = DirectClient(
        base_url="https://text.pollinations.ai/openai/v1",
        model="openai", api_key="pollinations-no-key-needed",
        min_interval_sec=45, reasoning_effort=effort,
    )
    try:
        obj, result = client.chat_typed(
            messages, TriageDraft, tools=[draft_tool_schema()], response_format_json=True
        )
        print(f"{label}: OK channel={result.channel} draft={obj.draft[:80]!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"{label}: FAIL {type(exc).__name__}: {str(exc)[:200]}")
    finally:
        client.close()
print("done")
