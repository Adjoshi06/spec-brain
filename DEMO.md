# Demo runbook — 3 minutes

Measured in the final scripted run (Opus 5, effort medium): before 21 s · inbox 12 s ·
substitute 63 s (live fetch + two sandboxed checks) · send 30 s · after 16 s — about 2.4 min
of agent time. Talk over the substitute turn; it is the long one. Before the demo: `python seed.py --reset --visualize`
(≈70 s) gives a clean memory with no substitution decision on record.

Setup before you walk up: the browser UI is running at http://localhost:8501
(`.venv\Scripts\python.exe -m streamlit run ui.py`). Click **↺ Reset memory** in the sidebar
if you rehearsed (~70 s), then walk the five numbered beat buttons in order; the email gate
shows an **Approve and send** button. The "Memory graphs" tab shows the three Cognee layers.
Docker Desktop running. Gmail is live: the rep email sits in your inbox and the sent request
arrives in the same inbox — keep your phone or a Gmail tab visible.

| Time | Say | Do |
|---|---|---|
| 0:00 | "My dad has run an architecture practice for decades. What he knows about products — what failed, what took 16 weeks, who to call — lives in his inbox and his head, and walks out the door when he retires. This is that memory, as an agent. Built on mine first." | — |
| 0:20 | "Three layers, hard walls in Cognee: his personal memory, the office standard, and the public web through Bright Data. Every fact is tagged with where it came from." | flash the graph tab |
| 0:35 | "First: what does it know *before*?" | `/before` → expect: spec is Sonar, **no substitution decision on record** |
| 0:50 | "Now the real trigger: my inbox." | `Anything in my inbox this week I should worry about on Mission St?` → `[INBOX]` finds the 16-week email, `[PERSONAL]` recalls the 8-week PO-to-site window and the 2025 lesson |
| 1:20 | "Find a substitute — and it is not allowed to do the numbers itself." | `Find me a substitute for the Mission St ceiling tile and check it against our standard.` → `[OFFICE STANDARD]` thresholds → `[PUBLIC]` candidates → live Bright Data fetch → `[CALCULATION · sandboxed]` table (point at *network none, read-only*) → recommendation with explicit gaps |
| 2:20 | "Then it acts — with my approval." | `Send the substitution request to the BuildCo PM.` → approval panel → `y` → show the email arriving → `[PERSONAL] decision is being written to memory` |
| 2:45 | "And now it remembers." | `/before` again → the decision, why, and the sources |
| 2:55 | "One architect's memory today; the firm-scale version is what I'm building as Archetype." | — |

## If something breaks on stage

- **Bright Data live fetch fails** → the tool prints `[PUBLIC · live] fetch failed`; say "it tells me instead of guessing" and let it fall back to the remembered page.
- **Gmail send fails** → the fallback writes `out\...-request.md`; open it.
- **Recall is slow** → talk over it: "graph completion, not keyword search."
- **Sandbox down** → the table says `UNSANDBOXED` in red; say "no silent failures — that is the whole point."
- **Model stalls** → Ctrl-C once returns to the prompt; re-ask.

## Questions judges may ask

- *Why not just RAG?* Three datasets are separate graphs; recall is scoped per layer so private notes never leak into public answers, and the decision written back becomes a node the next query walks. And an honest one: Cognee's graph-completion summariser hallucinated a "decision" in testing, so recall returns the raw cited chunks and the agent reasons — the harness decides, not the summariser.
- *Why the sandbox?* The model extracts values; the comparison is deterministic code with no network. Provenance over accuracy: you can always check.
- *What is real?* Real: scrapes, graph, sandbox, approval gate, email. Seeded: the notes are fictional, in my dad's voice, labelled as such.
