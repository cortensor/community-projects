## Building Blocks Tested

| block | how we used it | result |
|---|---|---|
| `Agent(output_type=...)` | pydantic `GoLiveReport` with `Literal` statuses | validates once the schema is in the message (finding 4) |
| `@tool` with `idempotent=True` | three read-only network tools | works |
| action policy | read-only tools still hit the confirmation prompt; approved in `approval_callback` | finding 1 |
| tool exposure | the first request of a turn lists only `submit_output`; tools come in later iterations | finding 2 |
| `@tool(dangerous=True)` + `forced_tools` + `approval_callback` | `save_report` behind human approval | works |
| `session_id` | one fresh session per run and agent (`golive-<host>-<ts>`, `-judge`, `-publish`) | a follow-up run in the same session lost the first message (finding 5) |
| `ProviderError` / `TurnTimeoutError` | free-tier 429 retried after 65 s; a timed-out investigator keeps the facts it already collected | works |
| provider pacing | none built in; we wrap the OpenAI-compatible adapter to stay under 6.5k tokens/min | finding 3 |

