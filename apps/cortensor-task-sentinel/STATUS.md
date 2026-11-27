# Status: Cortensor Task Sentinel

- **Version:** 0.1.0
- **Status:** active (Cortensor Hackathon #5 / DoraHacks #2418)
- **SDK:** OpenMinion 0.1.24 (`openminion>=0.1.24`), Python 3.11+ (tested on Python 3.13)
- **Demo provider:** Ollama (`gpt-oss:20b-cloud` via OpenAI-compatible `http://localhost:11434/v1`; supports Cortensor Portal preset with `CORTENSOR_API_KEY`)
- **Tests:** 29 offline tests passing (`uv run pytest -q`)

## Verified Evidence

- Live `openminion==0.1.24` local receipt: `outputs/live_model_run_receipt.json`
- Live `openminion==0.1.24` Cortensor Portal receipt: `outputs/cortensor_portal_run_receipt.json` (both tasks completed end-to-end on `oss-20b`: `722.6 s` certified, `651.6 s` rejected)
- Standalone repository: https://github.com/manderson240/cortensor-subnet-validator
- Live terminal demo video (H.264 MP4, 74 s, live Cortensor Portal `oss-20b`): https://github.com/manderson240/cortensor-subnet-validator/raw/main/docs/cortensor_live_demo.mp4
- Upstream SDK bug report & fix PR: https://github.com/openminion/openminion/issues/733 and https://github.com/openminion/openminion/pull/734

## Roadmap

- Add bounded worker memory/CPU resource limits inside a separate OS container alongside the AST gate
- Simplify Portal agent config once OpenMinion adds a first-class low-overhead preset flag for slow decentralized routers

## Known Issues

- `from openminion.modules.tool.executor import ToolExecutionBatch` still raises circular-import `ImportError` in PyPI `openminion==0.1.24` until PR `#734` is released.
- Non-deterministic `forced_tools` skipped workflows (`tool_calls: []` with 4 LLM calls) still occasionally occur on `0.1.24` and fail closed by design.
- On live Cortensor Portal (`https://api.cortensor.app/v1`), default OpenMinion pre-turn reflection/classification takes up to `414.0 s` before running tools and hits `600 s` timeouts, while OpenMinion also disables HTTP retries on Cortensor (`cortensor_portal_no_idempotency`). `write_agent_config("portal", ...)` disables `memory_enabled`, `auto_fact_extraction`, and `reflection` (leaving `thinking` at default so `gemma4` does not hit `invalid_task_context_update`) with a `900 s` turn timeout, and `sentinel.py` wraps Portal tasks in bounded retries.
