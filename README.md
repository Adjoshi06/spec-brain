# Spec Brain

**An architect's personal memory, as an agent.** Built solo at the *Battle of the Personal
Brains* hackathon (cognee × Bright Data × AWS, San Francisco, 2026-09-21).

My father has run an architecture practice for decades. What he knows about building products —
what he specified, what went wrong, what took 16 weeks instead of 6, who to call — lives in his
inbox, his Drive and his head, and walks out the door when he retires. Spec Brain is that memory
as an agent: it reads his mail and his meeting notes, remembers his decisions, checks the live
web, verifies a substitute deterministically in a sandbox, and sends the request or books the
follow-up — after he approves.

- **Written case:** [`SUBMISSION.md`](SUBMISSION.md) · **Demo runbook:** [`DEMO.md`](DEMO.md) · **Build plan:** [`PLAN.md`](PLAN.md)
- **Demo video:** [`artifacts/video/spec-brain-demo.webm`](artifacts/video/spec-brain-demo.webm) — the browser UI running all seven beats end to end, recorded by driving the live app (`make_video.py`)
- **Evidence:** [`artifacts/`](artifacts/) — scripted-run transcript, a generated substitution request, smoke results
- **Memory graphs:** [`graph/personal.html`](graph/personal.html) · [`graph/office.html`](graph/office.html) · [`graph/public.html`](graph/public.html)

## Architecture

```
                 ┌──────────────────────────── Strands Agent (Claude Opus 5) ────────────────────────────┐
                 │  system prompt: three tagged layers · never do the numbers · never act unapproved      │
   browser UI ──►│                                                                                       │
  (Streamlit)    │  recall_personal  recall_office  recall_public      ── Cognee (3 datasets, node sets) │
                 │  inbox_scan  drive_search  drive_read               ── Gmail / Google Drive           │
                 │  web_search  live_lookup                            ── Bright Data Web MCP            │
                 │  check_substitute                                   ── Docker sandbox (no network,    │
                 │                                                        read-only, caps dropped)       │
                 │  send_substitution_request  create_reminder   ◄── HumanInTheLoop approval gate        │
                 │  remember_decision                                  ── Cognee write-back              │
                 └───────────────────────────────────────────────────────────────────────────────────────┘

   [PERSONAL] his notes, decisions, lessons, contacts, Drive documents, and every decision the agent stores
   [OFFICE STANDARD] company data — the practice's acoustic ceiling standard
   [PUBLIC · url · date] real manufacturer pages scraped with Bright Data
   [INBOX] Gmail · [DRIVE] Google Drive · [CALCULATION · sandboxed] · [ACTION] email sent / event created
```

Datasets are hard walls in Cognee (one graph + vector store each), so layers never blend; every
fact the agent states carries the tag its tool returned; empty recall is "I don't have that in
memory", never a guess; the pass/fail comparison runs as code inside the container, not in the
model; and nothing is sent or scheduled until a human clicks Approve.

## Quickstart (Windows, Python 3.12)

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt streamlit
copy .env.example .env            # Anthropic (workspace-scoped) key, OpenAI key for Cognee, Bright Data token, your email
# Google: OAuth client JSON as credentials.json (Desktop app, or a Web client with http://localhost:8765/ registered);
#         enable the Gmail, Drive and Calendar APIs; add yourself as a test user.
docker pull python:3.12-slim      # the sandbox image
.venv\Scripts\python.exe smoke\brightdata_smoke.py     # scrape the manufacturer pages into seed\public\cache
.venv\Scripts\python.exe seed.py --reset --visualize   # build the three Cognee layers + graph\*.html
.venv\Scripts\python.exe smoke\google_smoke.py         # one-time consent; caches token.json
.venv\Scripts\python.exe -m streamlit run ui.py        # the demo UI on http://localhost:8501
```

`python demo.py` runs the five beats non-interactively and writes `out/demo-transcript.md`;
`python cli.py` is the terminal version; `pytest` covers the deterministic check.

## Layout

| Path | What |
|---|---|
| `agent.py` | Strands agent, twelve tools, system prompt, approval gate |
| `brain.py` / `seed.py` | Cognee wrapper (remember / recall / visualize on one event loop) and the seed pipeline |
| `web.py` | Bright Data hosted Web MCP client (scrape, search) |
| `google_io.py` | Gmail, Drive, Calendar with local-file fallbacks that say why |
| `spec_check.py` / `sandbox.py` | the deterministic check and the locked-down container that runs it |
| `ui.py` / `cli.py` / `demo.py` | browser UI, terminal UI, scripted run |
| `seed/` | fictional personal notes and office standard (persona voice), scraped public pages, Drive note text |
| `smoke/` | one runnable check per integration |
| `tests/` | unit tests for the check (TDD) |
| `artifacts/` | evidence from the runs |

## What is real and what is seeded

Real: the Cognee graph and recall, the Bright Data scrapes of real product pages, the Docker
sandbox, the Strands approval gate, the Gmail send, the Calendar event, the write-back to
memory. Seeded: the personal notes and the office standard are fictional and written in the
persona's voice (`seed/README.md`); the trigger email and the site-meeting Doc are ones I created
in my own accounts. No one else's data is read.

## Two findings kept on purpose

Cognee's graph-completion summariser hallucinated a "decision" from two unrelated notes, so the
agent's recall returns raw cited chunks and the reasoning model does the reasoning. Cognee's
session memory answered a write-back query with a cached stub until disabled (`CACHING=false`).
Both are in `SUBMISSION.md`; both are the brief's own principle — the harness decides, not the
summariser.
