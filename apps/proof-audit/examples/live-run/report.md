# ProofAudit Report: `proof-audit`

- **Verdict**: `READY`
- **Score**: `100/100`
- **Session ID**: `proof-audit-eff1f9debb`
- **Offline Fallback**: `False`

## Executive Summary

ProofAudit repository proof-audit is clean and ready: all four audit domains (manifest, SDK surface, endpoint reachability, smoke compile) passed with zero failures. Ten OpenMinion building blocks were detected across six Python files, the endpoint is reachable (HTTP 401, authentication required), and all files compile cleanly.

## OpenMinion Building Blocks Detected

- `@tool`
- `APIRuntime`
- `Agent`
- `AgentOutputValidationError`
- `ProviderError`
- `TurnTimeoutError`
- `approval_callback`
- `openminion CLI/doctor`
- `output_type`
- `session_id`

## Check Findings

| Check ID | Category | Status | Evidence | Fix |
| --- | --- | --- | --- | --- |
| `manifest.license` | manifest | **PASS** | LICENSE present (MIT License detected). | - |
| `manifest.readme` | manifest | **PASS** | README.md present (3462 bytes). | - |
| `manifest.openminion_pin` | manifest | **PASS** | requirements.txt pins openminion==0.1.24. | - |
| `manifest.gitignore` | manifest | **PASS** | .gitignore covers .venv, __pycache__, .openminion, and .env. | - |
| `manifest.secrets_hygiene` | manifest | **PASS** | No hardcoded secrets or disallowed labels detected in scanned repository files. | - |
| `sdk.surface_coverage` | sdk | **PASS** | Detected 10 OpenMinion building blocks across 6 Python files: @tool, APIRuntime, Agent, AgentOutputValidationError, ProviderError, TurnTimeoutError, approval_callback, openminion CLI/doctor, output_type, session_id. | - |
| `endpoint.reachability` | endpoint | **PASS** | Endpoint https://api.cortensor.app/v1/models responded with HTTP 401 in 1039.76 ms. | - |
| `smoke.py_compile` | smoke | **PASS** | py_compile succeeded on all 6 Python files. | - |

## Remediation Steps

No remediation required.
