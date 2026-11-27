## What We Learned

1. **Read-only tools still ask for confirmation, unless `min_scope="READ_ONLY"` is declared.** With the default
   `action_policy`, a `@tool(idempotent=True, tags=("read_only",), capabilities=("read_only", ...))` still returns
   `"openminion: Policy confirmation required ... reply yes"` as the agent's text, because the decorator default
   `min_scope="WRITE_SAFE"` wins over the tags (same root cause as openminion#464). With `output_type` set this
   surfaces as an `AgentOutputValidationError` whose input is the policy message, which is confusing; a distinct
   error type for a held tool call would make it obvious.
2. **The first request of every turn is the memory extractor, and it carries the whole agent prompt.** That call
   exposes only `submit_output` (schema `UserMessageCandidateReport`) plus the agent's full system prompt (~4.9k
   characters, here "call plugin.golive.inspect_home ..."), so a model replaying it alone answers "the inspection
   tools are not available". We first read it as the main turn hiding our tools. It is auto fact extraction, and it
   is switched off with a top-level `"brain": {"auto_fact_extraction": {"enabled": false}}` in `agents.json`
   (verified offline with `tools/measure_prompt.py`: the `submit_output` call disappears); putting the flag inside
   the agent profile does nothing. On a paced free tier it is one extra round trip per turn.
3. **A single turn is too big for an 8k tokens/min free tier.** The main turn sends ~17k characters of system prompt
   plus eight built-in tools (`tool.request`, `respond`, `coding`, `plan`, `research`, `decompose`, `clarify`,
   `review.diff`) when `Agent(tools=...)` is left at its default. Groq answered `413 Request too large ...
   Requested 8683` on `openai/gpt-oss-120b`. There is also no pacing for free-tier providers: the SDK's own retry
   (`max_retries: 2`, `backoff_ms: 300`) is far shorter than a 60 s rate window. A `tokens_per_minute` knob on the
   connection would make free tiers usable.
4. **`output_type` is not enforced on the model.** The judge answered a markdown table prefixed with
   `openminion: `; the SDK's JSON recovery found nothing to recover. A JSON schema placed at the end of `instructions`
   had no effect; the same schema inside the user message worked on the first try.
5. **A second `run()` in the same session did not see the first message.** After a validation failure we asked
   "reply with only the JSON object" in the same `session_id`; the model answered "no investigation data was
   provided". We now resend the facts with the retry.
6. **The freshness guard replaced a grounded answer.** The investigator called all three tools, yet its final text
   was "I couldn't provide a grounded current general answer because Missing exact-date evidence for an exact-date
   freshness answer". The tool facts were fine (the judge used them), but the turn's text was lost. A tool result
   that came from a live fetch could count as fresh evidence.
7. **Our own bug, caught by a real run:** the first live run flagged a 697-character title on
   capegraniteconnection.com. The page title is 63 characters; our parser was concatenating the `<title>` elements of
   inline SVG icons. Fixed in `checks.py` with a regression test. The agent repeats whatever the tools report, which
   is why the facts layer has its own tests.

