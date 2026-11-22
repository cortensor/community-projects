# Submission Runbook — Cortensor Hackathon #5 (`#2418`)

## 1. Event Gates & Deadlines

- **Event:** Cortensor Hackathon #5 (`https://dorahacks.io/hackathon/2418/detail`)
- **Prize Pool:** `$1,150 USD` equivalent in `$COR` (`50%` liquid `$COR` upfront + `50%` 1-month Cortensor staking lock)
- **Track:** Default Track (`4697`)
- **Submission Window Close:** December 18, 2026 PT (`2026-12-19T07:59:00Z`)
- **Prior Hackathon Reuse Count:** `0` (`< 5` anti-farming threshold satisfied)

## 2. Pre-Submission Verification Commands

Run all deterministic gates from the subproject root before publishing or opening the Hackathon #5 PR:

```bash
# 1. Regenerate live neural model receipt and 6 empirical probe artifacts
.venv/bin/python -m src.cli

# 2. Run pytest suite + negative-control mutation tripwire
.venv/bin/pytest tests -q
CORRUPT_GATE_CONTROL=1 .venv/bin/pytest tests -q

# 3. Verify Dark Studio UI artistry gate (M >= 0.68)
python3 /Users/zerbytheboss/.gemini/config/artistry_harness.py web/diagnostic_console.html

# 4. Validate DoraHacks Build markdown (0 errors, 0 warnings)
python3 /Users/zerbytheboss/.gemini/config/skills/dorahacks-builder/scripts/dorahacks_preflight.py validate-build \
  --body-file submission/BUIDL_DRAFT.md \
  --prior-submissions 0 \
  --github-url "https://github.com/HindsightWise/minionbench-ops-openminion" \
  --video-url "https://github.com/HindsightWise/minionbench-ops-openminion/raw/main/outputs/demo_walkthrough.mp4" \
  --require-github \
  --require-video \
  --json
```

## 3. Recording the 1–5 Minute Demo Video

1. Serve the project locally (`python3 -m http.server 8765`) and open `http://127.0.0.1:8765/web/diagnostic_console.html`.
2. Show `.venv/bin/python -m src.cli` executing the OpenMinion `0.1.24` multi-tool release triage workflow (`inspect_workspace_manifest`, `audit_python_module_risks`, `check_cortensor_config_posture`) and writing `outputs/live_model_run_receipt.json`.
3. Walk through the Dark Studio Diagnostic Console (`1`–`6` probe tabs, Cortensor Portal `max_retries=0` vs Router `455.0s` posture viewer, and the 5 `What We Learned` upstream findings).
4. Upload the 2–3 minute recording and update `video_url` in `submission/buidl_draft.json` and `submission/BUIDL_DRAFT.md` prior to submitting on `dorahacks.io` and opening the Hackathon #5 repository PR.
