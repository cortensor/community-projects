# Browser preview — try-out page source

`index.html` is the source of the Cortensor try-out page (the same page
hosted as a Muse artifact for Allen). It is a single self-contained file:
open it in any browser, no build step, no server, no key, no login.

## Launch

```sh
# from the repo root
python3 -m http.server 8000 --directory docs/browser-preview
# then open http://localhost:8000/index.html
```

Or just double-click `index.html` — it works from `file://` too (all data
is embedded; the only network calls are the live model calls to
Pollinations).

## What it does

Four tabs:

1. **Issue 分流 (live)** — paste an issue (prefilled with the real
   `openminion/openminion#778`), click 开始分流. One call to the
   Pollinations free endpoint (`https://text.pollinations.ai/openai/v1`,
   model `openai`, no key), `response_format: {type: "json_object"}`,
   105 s timeout. **Simplified one-call preview:** classify only. It
   does not fetch comments / linked PRs / CODEOWNERS, has no memory, and
   never posts anything — those are the CLI's job. Suggested labels are
   filtered against the repo's real label list (embedded from
   `fixtures/openminion-issue-778.json`); invented labels are dropped and
   the drop is shown.
2. **论文截稿** — the 48 deadlines in the 120-day window (embedded data
   from the paper-deadline agent's verified CSVs) plus a live model brief
   with a labelled template fallback.
3. **黑客松追踪** — the 2026-11-17 recorded run (cannot re-run in-page:
   CORS / JS rendering / reCAPTCHA).
4. **Build texts (EN)** — the three DoraHacks Build submission texts,
   per-field copy buttons.

Footer: everything $0, no login, no key; free-tier limit 1 reply / 45 s /
IP (HTTP 402) with one bounded auto-retry after `max(47 s, Retry-After)`.

## Smoke test

```sh
python3 scripts/smoke_browser_preview.py --no-live   # static checks only
python3 scripts/smoke_browser_preview.py --live      # + 1 live Pollinations call ($0)
```

The static checks verify the hardening (JSON mode on the triage call
only, 105 s timeout, Retry-After handling, bounded auto-retry, tool_calls
envelope parsing, label list == fixture, cooldown in localStorage, Start
disabled in flight) and that the #778 prefill matches the fixture. The
live check posts the page's exact triage request and requires valid JSON
with all 7 keys and `issue_type == "bug"`.

## How this file relates to the hosted artifact

The hosted artifact page and this file are the same page: this copy was
exported from the artifact, then hardened per the 2026-11-17 ChatGPT
audit (see `docs/WHAT_WE_LEARNED.md` §17). If the artifact is edited
again, re-export it here and re-run the smoke test — do not let the two
copies drift.
