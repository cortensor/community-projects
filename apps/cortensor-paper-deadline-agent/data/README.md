# data/ — verified venue tables (copied verbatim, 2026-11-16)

Public venue information only — no personal data.

| File | Rows | What it is |
|------|------|-----------|
| `ccf2026-full.csv` | 682 + header | CCF 2026 official 7th edition list (conferences 387, journals 295; A 95, B 245, C 342), cross-checked against the official PDF 2026-03-31 |
| `deadlines-all-conferences.csv` | 390 + header | Next-cycle submission deadlines for the 390 CCF conferences (387 + COLM, ICVR, SSDM), each checked against the venue's official page on 2026-11-16 |
| `journals-submission.csv` | 295 + header | Submission method / cycle / fixed deadlines for the 295 CCF journals, checked 2026-11-16 |
| `law-submission.csv` | 24 + header | Law venues (21 from the tracker + 3 SSCI); only CLSR is in CCF |

## Verification status (the honesty core of this project)

Every row carries a `status` verified on 2026-11-16:

- `verified` (conferences 119, journals 284, law 21) — a date for the next
  cycle was found on the official page.
- `cycle_not_announced` (conferences 231, journals 4) — the next cycle is
  not announced; any date in the row is from the last known cycle.
- `not_found` (conferences 40, journals 7, law 3) — no authoritative date
  could be found.

Some rows were verified from search-index text of the official page rather
than a direct page open; the agent reports the `status` as recorded and
never upgrades it. Rows with no future parsable date are reported as
`date_unclear` and never listed as dated deadlines.

## Checksums (sha256, must match the tracker originals)

- `ccf2026-full.csv` — `4f4fc76007307398f06560b125ca28d74683b18825dc37be1f359e24290f4eb1`
- `deadlines-all-conferences.csv` — `ebe68064630e3cf5cecdff9628cd8638c5eb8abfb295341e7d535aa232bb2a2c`
- `journals-submission.csv` — `3e3fdee9e234360f0244f8b8816e723e363f446b1421748288d7cdff44530493`
- `law-submission.csv` — `1f5e471753f2b05646826b6cec952fd8fb30e14d28d68be167ce50a050ee6828`

## Reminder rule

Remind 120 days ahead; re-check the tables monthly (the tracker's monthly
review cadence). To refresh the data, replace these four files with a newly
verified export and update the checksums above.
