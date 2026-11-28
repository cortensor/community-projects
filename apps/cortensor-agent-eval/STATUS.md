# Cortensor Agent Eval — Status

- **Version:** `0.1.0`
- **SDK Target:** `openminion==0.1.24`
- **Status:** Active / Verified on Windows & Python 3.11
- **Tests:** `6/6` end-to-end, security, and SDK reproducer tests passing (`pytest -v`)
- **Known Limitations:** Live inference against `https://api.cortensor.app/v1` requires a valid `CORTENSOR_API_KEY`; without a key, the evaluator probes endpoint reachability (HTTP `401`) and triggers deterministic offline fallback cleanly.
