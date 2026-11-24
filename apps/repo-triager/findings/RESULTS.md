# Reproduction results

Captured on 2026-11-24T12:27Z with openminion 0.1.24, Python 3.12.16.

Each block is the literal output of the script above it; every one needs no credential and no network.

## `findings/repro_instructions_truncation.py`

```
$ python findings/repro_instructions_truncation.py
========================================================================
FINDING 1 — instructions truncation
========================================================================
instructions sent : 2599 characters, 30 rules, sentinel at the end
turn state        : completed
rules that reached the model: ['01', '02', '03', '04', '05', '06', '07', '08']
sentinel reached the model   : False

RESULT: REPRODUCED — the later rules never reach the model.
        8 of 30 rules survived; everything from rule 09 onward was dropped.
```

## `findings/repro_structured_output_schema.py`

```
$ python findings/repro_structured_output_schema.py
========================================================================
FINDING 2 — output_type schema never reaches the model
========================================================================
raised: AgentOutputValidationError: Reply did not validate against Triage: 1 validation error for Triage
  Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='openmini

Triage schema present in any model request: False
RESULT: REPRODUCED — the request asks for no particular shape, so the
        prose reply fails validation after the model call was paid for.
        Workaround used by Repo Triager: put the JSON schema in the
        task message (see repo_triager/agent.py: OUTPUT_SCHEMA).
```

## `findings/repro_policy_gate_vs_output_type.py`

```
$ python findings/repro_policy_gate_vs_output_type.py
========================================================================
FINDING 3 — policy denial vs. structured output
========================================================================
raised: AgentOutputValidationError
message: Reply did not validate against Applied: 1 validation error for Applied
raw reply text: 'openminion: Confirmation denied. The action was not run.'

tool executed despite the denial: False
RESULT: REPRODUCED — the write was correctly blocked, but the caller
        receives AgentOutputValidationError instead of a policy result.
        Workaround: run gated writes without output_type.
```

## `findings/repro_session_scope.py`

```
$ python findings/repro_session_scope.py
========================================================================
FINDING 4 — session id scope validation
========================================================================
scope pattern: ^(session|agent|project|global):[A-Za-z0-9._:-]+$
'session:repo-triager:openminion_openminion'     valid: True
'session:repo-triager:openminion/openminion'     valid: False

turn with session_id 'session:repo-triager:openminion_openminion'   -> completed
turn with session_id 'repo-triager:openminion/openminion'           -> completed

RESULT: REPRODUCED — the invalid scope is detected by the memory layer
        while the turn reports success. Repo Triager slugifies its
        session ids (openminion_openminion) for exactly this reason.
```

## `findings/repro_operator_id_getpwuid.py`

```
$ python findings/repro_operator_id_getpwuid.py
========================================================================
FINDING 5 — operator id derived from getpwuid
========================================================================
uid 1000 has a passwd entry: False
getpass.getuser() usable        : KeyError: 'getpwuid(): uid not found: 1000'

without USER set:
{
  "ok": false,
  "error": {
    "code": "UNKNOWN",
    "message": "'getpwuid(): uid not found: 1000'"
  }
}

RESULT: REPRODUCED — set USER (or add a passwd entry) and it works;
        the error text does not name the cause.
```

## `findings/repro_memory_search_truncation.py`

```
$ python findings/repro_memory_search_truncation.py
========================================================================
FINDING 6 — memory.search truncates structured content
========================================================================
memory.search calls captured: 3
{"outputs":{"content":"memory search returned 1 record(s)","data":{"count":1,"query":"triage decision severity","records":[{"access_count":0,"confidence":0.5,"content":{"component":"[TRUNCATED]","labels":"[TRUNCATED]","severity":"[TRUNCATED]"},"created_at":"2026-11-24T12:29:18.979353+00:00","deleted_at":null,"deleted_reason":null,"entities":[],"event_time":"2026-11-24T12:29:18.979353+00:00","evide

RESULT: REPRODUCED — the record's values arrive as [TRUNCATED];
        only the record id, key, and metadata remain usable.
```

## `findings/measure_turn_cost.py`

```
$ python findings/measure_turn_cost.py
========================================================================
MEASUREMENT — per-turn model calls
========================================================================
decision          : S2 area:tools
LLM calls         : 12
tool calls        : 3
input tokens      : 75298
output tokens     : 828
elapsed (ms)      : 1040
calls by purpose  :
    act                    5
    entry                  2
    freshness_classify     1
    judge                  3
    reflect                1

Reading: the tool loop is the small part. The fixed per-turn calls
(afe + freshness + reflect + judge) dominate; a 5-issue batch pays them
five times over, which is why the CLI keeps batches small and caches
the issue snapshot locally.
```

