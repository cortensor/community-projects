# Triage plan — #859 Reject malformed explicit plugin contract versions before loading

- Repository issue: https://github.com/openminion/openminion/issues/859
- Severity: **S2** (A malformed plugin contract version is accepted instead of rejected, so a broken plugin loads and fails later.)
- Component: `area:tools`
- Type: `bug`
- Labels to add: `bug`, `area:tools`
- Possible duplicates: none
- Confidence: 0.78
- Next action: `ready-to-label`
- Mode: **dry run** — staged locally, nothing was written to GitHub

## Reply draft

Thanks for the precise report — the contract-version check should reject an explicit but malformed version before any plugin module is imported, and right now it falls through to the lenient path.

We are tracking this as an S2: a bad plugin can load successfully and then fail during the first tool call, which is much harder to diagnose. I have added `area:tools` and put it in front of the plugin loader work; no timeline yet, but I will comment here when a branch is up.
