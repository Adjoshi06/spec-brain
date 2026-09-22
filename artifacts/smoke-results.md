# Smoke results (2026-09-21, Windows 11, Python 3.12)

Every integration was exercised on its own before the agent was wired; numbers below are from
those runs (`smoke/*.py`) and the two scripted demo runs.

## Cognee 1.6.0 (local: SQLite + LanceDB + Ladybug, OpenAI gpt-4o-mini + text-embedding-3-small)

| Step | Result |
|---|---|
| `forget(everything=True)` | 0.1–13 s |
| seed `personal` (6 notes, 4 node sets) | 4–15 s per node-set batch, ~22 s total |
| seed `office` (1 standard) | 7–9 s |
| seed `public` (7 scraped pages) | 15–30 s |
| full reset + three layers + three graphs | 63–71 s |
| `recall` CHUNKS, top_k 6 | 1.6–4.2 s |
| `recall` GRAPH_COMPLETION | ~2 s — **hallucinated** a decision on an empty question (see SUBMISSION.md) |
| write-back → recall of the stored decision | top hit, 4 s (after `CACHING=false`) |

## Bright Data hosted Web MCP (free/rapid tools: search_engine, scrape_as_markdown, batches)

| Page | Time | Chars | NRC / CAC / Class A in text |
|---|---|---|---|
| Rockfon Sonar | 7.8 s | 13,720 | yes / yes / yes |
| Rockfon Koral | 37.0 s | 13,279 | yes / no / yes |
| USG Mars | 5.7 s | 15,410 | yes / yes / yes |
| USG Mars High-NRC | 22.5 s | 16,434 | yes / yes / yes |
| Armstrong ULTIMA High-NRC | 99.0 s | 648 | blocked page |
| Armstrong ULTIMA Lay-In | 43.8 s | 31,169 | yes / yes / yes |
| CertainTeed Symphony f | 9.1 s | 17,639 | no / no / no (marketing page) |

Average 32 s per scrape; live on-stage re-fetch of the USG page ~20 s. The REST `/request` PDF
path returned non-PDF content and was not used.

## Docker sandbox (`python:3.12-slim`, `--network none --read-only --cap-drop ALL --user 65534`)

- `spec_check.py` inside the container: 0.19–0.56 s per check.
- `docker inspect`: `network=none readonly=true capdrop=[ALL] pids=128 user=65534:65534`.
- In-container network probe: `urlopen('https://example.com')` → `URLError: Temporary failure in name resolution`.

## Strands 1.56.0 + Claude Opus 5 (effort medium)

Scripted five-beat run: before 20.5 s · inbox 11.9 s · substitute 63.0 s (live fetch + two
sandboxed checks) · send 30.1 s · after 15.8 s. Approval gate via `HumanInTheLoop`
(interrupt/resume in the browser UI, inline `ask` in the CLI).

## Google (web-type OAuth client, loopback `http://localhost:8765/`, test user)

- Gmail read: trigger email found 5 s after sending. Gmail send: real message id returned.
- Drive: file listing and Google-Doc export to text verified.
- Calendar: `calendar.events` scope verified read-only; `create_reminder` creates real events after approval.
- Errors met and fixed on the way: `redirect_uri_mismatch` (web client without a loopback URI),
  "has not completed the Google verification process" (account not on the test-user list),
  `accessNotConfigured` (Gmail/Calendar API not enabled).

## Tests

`pytest tests/test_spec_check.py` — 12 passed (thresholds, unknown-vs-fail, size normalisation
for 2x2 / 2' x 2' / 600 x 600 mm, CLI JSON contract).
