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

Twelve tools: `recall_personal`, `recall_office`, `recall_public`, `inbox_scan` (Gmail),
`drive_search` + `drive_read` (Google Drive; a document read is stored into personal memory),
`web_search` + `live_lookup` (Bright Data), `check_substitute` (Docker sandbox),
`send_substitution_request` (Gmail) and `create_reminder` (Google Calendar) — both gated by
Strands `HumanInTheLoop` — and `remember_decision`.

Two interaction modes: question-driven (the five demo beats) and autonomous — a **risk scan**
that reads inbox and Drive, cross-checks every active project against memory and the office
standard, and returns ranked risks each with one proposed, gated action.

Personal data sources used, per the brief: Gmail, Google Drive, Google Calendar, local files.

The model never compares numbers: `check_substitute` runs `spec_check.py` inside a container
with `--network none --read-only --cap-drop ALL`, as user `nobody`. If Docker is missing the
check still runs but is labelled `UNSANDBOXED` — nothing fails silently.

## Before / after evidence

From the scripted run (`python demo.py`; full transcript in `artifacts/demo-transcript.md`, the
generated email in `artifacts/substitution-request.md`, timings in `artifacts/smoke-results.md`;
Claude Opus 5 through Strands, effort medium).

**Before** — "Have we made any substitution decision on the Mission St ceiling? What is on record?" (23 s)
> **No substitution decision is on record yet.** … Original spec [PERSONAL, decision 2026-06-12]
> Rockfon Sonar, 2x2 lay-in … rep quoted ~6 weeks **verbally, not in writing** … Schedule
> [PERSONAL, note 2026-08-20] BuildCo wants the PO placed **by 25 Sept 2026** (~8 weeks PO-to-site).

**Inbox** (11 s) — finds the rep's email, ties it to memory:
> [INBOX] Sonar lead time is now **16 weeks from PO, not 6** … 16 weeks from a 25 Sept PO lands
> in mid-January, well past Northgate's **December move-in** [PERSONAL] … exactly the failure
> mode from [PERSONAL, lesson 2025-03-04] Harrison St.

**Substitute** (66 s) — office standard → candidates in memory → **live** Bright Data fetch of
the USG page → two sandboxed checks:
> | Config | NRC | CAC | Fire | Size | Recycled | Verdict |
> |---|---|---|---|---|---|---|
> | 0.90 NRC / 30 CAC | pass 0.90 | **fail 30** | pass Class A | pass 24x24 | pass 71% | [CALCULATION] **FAIL** |
> | 0.85 NRC / 35 CAC | pass 0.85 | pass 35 | pass Class A | pass 24x24 | pass 71% | [CALCULATION] **PASS** |
>
> **Lead time is not stated on the page — I don't have it in memory.** … Armstrong ULTIMA: the
> live page returned no NRC or CAC figures, so I can't check it.

**Send** (34 s) — approval gate → substitution request sent → decision written to memory.

**After** — the same question, asked again in the same scripted run after the send:
> Yes — there is now a substitution decision on record, dated today. **[PERSONAL decision,
> 2026-09-21]** Original spec: Rockfon Sonar 2x2 lay-in … dropped. Why: lead time rose from ~6 to
> **16 weeks from PO** … Substitute: **USG Mars High-NRC** … the **0.85 NRC / 35 CAC** option.
> Check result: PASSES all five … Excluded: the 0.90 NRC variant — FAILED on CAC 30. Source:
> usg.com/…mars-high-nrc-acoustical-panels-88137, retrieved 2026-09-22 … Three open items carried
> in the decision: lead time in writing before the 25 Sep PO; a finish sample for Northgate; brief
> the installer on edge handling.

The raw recall behind that answer (direct tool call, 4 s):
> [PERSONAL] [personal decision, 2026-09-21] Mission St, Level 3 open office (Northgate Partners)
> — ceiling substitution sent 2026-09-21. The specified Rockfon Sonar 2x2 lay-in went from an
> indicated ~6 weeks to 16 weeks from PO … Proposed substitute: USG Mars High-NRC … primary
> configuration 0.85 NRC / 35 CAC, which passed a sandboxed check against the office standard on
> all five attributes … The 0.90 NRC / 30 CAC configuration … FAILED on CAC … Source:
> usg.com/en-US/p/product/mars-high-nrc-acoustical-panels-88137, retrieved 2026-09-22 … Lead time
> is not published on the manufacturer page, so nothing is confirmed until BuildCo replies in
> writing.
> sources: document_name=text_2153d9fc…; chunk_id=fc3b9b40-…

A second honest finding: in the first scripted run this recall returned a two-word stub
("Got it.") — Cognee's session memory (on by default) answered from a cached turn instead of
searching. `CACHING=false` fixed it; the run above is the fixed behaviour.

## What is real and what is seeded

- Real: Cognee graph + recall, Bright Data scrapes of real manufacturer pages, the Docker
  sandbox, the Strands approval gate, the Gmail send, the decision written back to memory.
  (The scripted runs used the local `.eml` inbox and file-based send because Google OAuth was
  still being set up; live Gmail read/send and Drive listing were verified afterwards and the
  tools switch to them automatically once a token exists — falling back, with a visible label,
  if Gmail errors.)
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
