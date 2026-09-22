# Spec Brain — an architect's personal memory, as an agent

**Battle of the Personal Brains Hackathon · 2026-09-21 · solo build**

## What it is

My father has run an architecture practice for decades. What he knows about building
products — what he specified, what went wrong, what took 16 weeks instead of 6, who to call —
lives in his inbox and his head, and walks out the door when he retires. Spec Brain is that
personal memory as an agent. It reads his inbox, remembers his decisions, checks the live web,
verifies a substitute deterministically in a sandbox, and sends the request — after he approves.

## The brain (Cognee)

Three datasets, kept as hard walls so layers never blend, each tagged on every answer:

| Tag | Cognee dataset | What is in it |
|---|---|---|
| `[PERSONAL]` | `personal` | his notes, project decisions, lessons, schedule, contacts, and every decision the agent stores |
| `[OFFICE STANDARD]` | `office` | the practice's acoustic ceiling standard (company data) |
| `[PUBLIC · url · date]` | `public` | real manufacturer product pages scraped with Bright Data |

Empty recall is reported as "I don't have that in memory" — never a guess.

**A finding from testing, kept on purpose.** Cognee's `GRAPH_COMPLETION` search (its own
small-model summariser) answered a deliberately empty question — "what did we decide about the
Bayview *flooring*?" — with a confident, false decision blended from two unrelated notes. So the
agent's recall tools use `CHUNKS`: the stored notes come back verbatim with document ids, and
the reasoning model cites them. Same graph, same node sets, same write-back; the summariser is
just not allowed to be the source of truth.

## The agent (AWS Strands + Claude)

Nine tools: `recall_personal`, `recall_office`, `recall_public`, `inbox_scan` (Gmail),
`web_search` + `live_lookup` (Bright Data), `check_substitute` (Docker sandbox),
`send_substitution_request` (Gmail, gated by Strands `HumanInTheLoop`), `remember_decision`.

The model never compares numbers: `check_substitute` runs `spec_check.py` inside a container
with `--network none --read-only --cap-drop ALL`, as user `nobody`. If Docker is missing the
check still runs but is labelled `UNSANDBOXED` — nothing fails silently.

## Before / after evidence

<!-- filled from out/demo-transcript.md -->

**Before** — "Have we made any substitution decision on the Mission St ceiling?"
> _(answer before the run)_

**The run** — inbox → memory → live web → sandboxed check → approval → email → remember.

**After** — same question:
> _(answer after the run, with sources)_

## What is real and what is seeded

- Real: Cognee graph + recall, Bright Data scrapes of real manufacturer pages, the Docker
  sandbox, the Strands approval gate, the Gmail send, the decision written back to memory.
- Seeded for the demo: the personal notes and the office standard are fictional and written
  in the persona's voice (see `seed/README.md`). The trigger email is one I sent myself.
- Not read: anyone else's inbox.

## Run it

```
uv venv --python 3.12 .venv && uv pip install -r requirements.txt
copy .env.example .env   # fill keys (a workspace-scoped Anthropic key, or set ANTHROPIC_WORKSPACE_ID);
                         # drop credentials.json (Google OAuth desktop client) in the root
python smoke\brightdata_smoke.py     # scrapes the product pages into seed/public/cache
python seed.py --reset --visualize   # builds the three Cognee datasets, writes graph/*.html
python cli.py                        # live demo   |   python demo.py   # scripted run
```

## Sponsor stack

Cognee (memory: datasets, node sets, remember/recall, graph HTML) · Bright Data (public layer,
hosted Web MCP from Strands) · AWS Strands Agents (tools, human-in-the-loop, streaming) ·
Docker (sandboxed deterministic check) · Gmail/Drive (personal data + the action).
