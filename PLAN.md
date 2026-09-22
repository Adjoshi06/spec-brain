# Spec Brain — Dad's personal specification memory, as an agent

*Battle of the Personal Brains Hackathon — 2026-09-21 — Bright Data SF. Solo build.*

## One sentence

An architect's personal memory of every product decision — what was specified, what went
wrong, who to call — lives in their inbox and their head and walks out the door when they
retire. Spec Brain is that memory as an agent: it reads the inbox, remembers the decisions,
checks the live web, verifies a substitute deterministically, and sends the request — with
the human approving the action.

## Persona and data (be honest on stage)

- **Whose brain:** my father's — he has run an architecture practice for decades.
- **Whose accounts:** mine (Gmail, Drive). Seed notes are written in his voice and marked
  *demo data* in this repo. No one else's inbox is read.
- **Three layers, always labeled** (this is the Luma page's own wording — "reason across
  personal, company, and public data"):

| Layer | Cognee dataset | Node sets | Source |
|---|---|---|---|
| Personal | `personal` | `inbox`, `drive`, `note`, `lesson`, `contact`, `decision` | Gmail, Drive doc, local notes, decisions the agent stores |
| Company | `office` | `standard` | The office acoustic-ceiling standard (5 lines) |
| Public | `public` | `datasheet` | Bright Data scrapes of real manufacturer product pages |

Datasets are hard walls in Cognee (separate graph + vector stores). Every fact the agent
returns carries its layer label. Empty recall → "unknown", never a guess. The model never
does the numeric comparison itself.

## Agent and tools (AWS Strands, Claude via Anthropic API)

| Tool | Backed by | Label |
|---|---|---|
| `recall_personal(q)` | `cognee.recall(datasets=["personal"])` | `[PERSONAL]` |
| `recall_office(q)` | `cognee.recall(datasets=["office"])` | `[OFFICE STANDARD]` |
| `recall_public(q)` | `cognee.recall(datasets=["public"])` | `[PUBLIC · page · retrieved]` |
| `inbox_scan(query)` | Gmail API read (fallback: `personal_data/*.eml`) | `[INBOX]` |
| `live_lookup(url_or_query)` | Bright Data hosted MCP: `search_engine`, `scrape_as_markdown` | `[PUBLIC · live · url · now]` |
| `check_substitute(spec, candidate)` | deterministic `check_substitute.py` executed in a Docker sandbox | `[CALCULATION · sandboxed]` |
| `send_substitution_request(to, subject, body)` | Gmail send, gated by Strands `HumanInTheLoop` | — |
| `remember_decision(text)` | `cognee.remember(dataset="personal", node_set=["decision"])` | — |

## Demo script (3 minutes)

0. **Before:** "What did we decide on the Mission St ceilings?" → *unknown*. Graph HTML open.
   A rep email ("Sonar lead time now 16 weeks") is sitting in the inbox.
1. "Anything in my inbox I should worry about on Mission St?" → `inbox_scan` finds the
   email → `recall_personal` says Sonar is specified on Mission St and install is in 9 weeks
   → the agent names the problem.
2. "Find me a substitute." → `recall_office` (the standard) + `recall_public` (seeded
   datasheets) → shortlist → `live_lookup` re-scrapes the top candidate's page live →
   `check_substitute` prints a pass/fail table from the sandbox → recommendation with
   labeled sources and explicit gaps ("recycled content not on the page").
3. "Send the substitution request to the contractor." → draft → **approve y/n** → real
   email → `remember_decision`.
4. **After:** repeat step 0 → answered, with provenance and the reason.

## Sponsor mapping

- **Cognee** — the brain: three datasets, node sets, `remember/recall`, graph visualization,
  `push` to Cognee Cloud at the end if time allows.
- **Bright Data** — the public layer: seed scrapes during setup, one live re-verification on stage.
- **AWS Strands** — the agent: tools, `HumanInTheLoop`, streaming tool calls, `DockerSandbox`.
- **Docker** — the sandbox that runs the deterministic compliance check (`--network none`,
  read-only, all capabilities dropped). `sbx` microVM only if it installs cleanly.
- **Personal data** — Gmail read/send, Drive read, local files.

## Fallback ladder (never silent — the UI prints which rung is active)

- Gmail read → local `.eml` files. Gmail send → SMTP app password → `out/request.md` opened in browser.
- Bright Data hosted MCP → `npx @brightdata/mcp` (stdio) → REST `POST /request`.
- Docker sandbox → local subprocess, printed as `UNSANDBOXED`.
- Cognee completion search hangs → `SearchType.CHUNKS`.

## Build order and verification

1. Env: venv (Python 3.12), install, `.env`, Docker Desktop up, `python:3.12-slim` pulled.
2. Smoke tests, one per integration, each a runnable script under `smoke/`:
   cognee round-trip; one Bright Data scrape; sandbox echo; Gmail list + Drive list.
3. `check_substitute.py`: pure function + unit tests (TDD) — NRC ≥, CAC ≥, fire class in
   allowed set, recycled content ≥, size match.
4. Seed: `seed/personal/*.md` (Dad's voice), `seed/office/standard.md`, `seed/public/`
   (Bright Data scrapes of Rockfon Sonar, Rockfon Koral, USG Mars, USG Mars High-NRC,
   Armstrong Ultima, CertainTeed Symphony f) → `seed.py` → `graph/*.html`.
5. Agent: `agent.py` (tools, system prompt, HITL), `cli.py` (Rich streaming).
6. `demo.py`: the four turns, non-interactive, run once end-to-end before rehearsing.
7. `SUBMISSION.md`: before/after evidence, screenshots, architecture, what is real vs seeded.

## Timeline (adjust to the deadline announced at kickoff)

16:20–16:50 env + smoke · 16:50–17:30 seed + graph · 17:30–18:30 agent + HITL + sandbox ·
18:30–19:00 demo.py rehearsal, SUBMISSION.md, optional Cloud push · then buffer.
