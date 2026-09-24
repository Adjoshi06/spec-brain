# Spec Brain — Agent Guidance

**Repo:** Adjoshi06/spec-brain — an architect's personal memory as an agent (hackathon build). A Strands
agent (Claude via Anthropic) with twelve tools: Cognee memory layers (personal / office standard / public
web), Gmail + Drive + Calendar I/O, Bright Data web scraping, a deterministic substitution check run inside
a locked-down Docker sandbox, and a human approval gate before anything is sent.

## Stack

- **Runtime:** Python (README quickstart targets 3.12; sandbox validated on 3.13)
- **UI:** Streamlit (`ui.py`), terminal UI (`cli.py`), scripted run (`demo.py`)
- **Memory:** Cognee 1.6.0 (graph + vector layers, OpenAI-backed embeddings)
- **Agent:** strands-agents[anthropic]; **Web:** Bright Data hosted Web MCP
- **Sandbox check:** `spec_check.py` runs inside a `python:3.12-slim` Docker container (no network)

## Commands (validated in sandbox)

```bash
pip install -r requirements.txt streamlit     # deps
cp .env.example .env                          # then fill keys (see Env below)
python -m streamlit run ui.py                 # browser UI — binds the next free port (8501 default; observed 8502 when 8501 busy). Parse "Local URL:" from startup output.
python -m pytest tests/ -q                    # 12 unit tests for the deterministic check
python -c "from spec_check import check_substitute; print(check_substitute({'nrc_min':0.85,'cac_min':35,'fire_classes':['Class A'],'size':'24x24','recycled_min':0.30},{'nrc':0.90,'cac':38,'fire_class':'Class A','size':'24x24','recycled':0.42})['verdict'])"
                                              # deterministic check → PASS
python demo.py                                # five scripted beats → out/demo-transcript.md (needs real keys)
python seed.py --reset --visualize            # build Cognee layers + graph/*.html (needs OpenAI key)
```

Do not assume the UI port — always read `Local URL:` from Streamlit's startup output.

## Env (see `.env.example`)

Required for the full agent flow (real keys, no sandbox substitutes): `ANTHROPIC_API_KEY`
(+ optional `ANTHROPIC_WORKSPACE_ID`), `LLM_API_KEY` / `EMBEDDING_API_KEY` (OpenAI, for Cognee),
`BRIGHTDATA_API_TOKEN`, Google OAuth `credentials.json` (Gmail/Drive/Calendar), `CONTRACTOR_EMAIL`,
`USER_NAME`. Cognee storage paths (`DATA_ROOT_DIRECTORY`, `SYSTEM_ROOT_DIRECTORY`) default to a
Windows path in `.env.example` — point them inside the repo on other platforms. `CACHING=false` and
`LOG_LEVEL=ERROR` are deliberate demo hygiene; keep them.

Safe local dummies let the UI and tests run, but NOT the agent chat, seeding, scraping, or Google I/O —
those need real credentials and (for `spec_check` in-container mode) Docker.

## Codebase map

See [codebase-map.md](codebase-map.md).

## Local verification

1. `python -m pytest tests/ -q` — must pass (12 tests).
2. Start the UI, confirm the `Local URL:` port answers HTTP 200 (also `/_stcore/health`).
3. Run the `check_substitute` one-liner above — must print `PASS`.

## Snapshot

- **snapshotId:** `adcrvj3qlgiq1ht8xnw2:default`
- **captured:** 2026-09-24T19:07:53.684Z
- **state:** deps installed (pip, system Python 3.13), `.env` present with safe local dummy values,
  Streamlit UI was running (tmux session `dev`, log `/tmp/streamlit.log`). No Docker daemon; no real API keys.

## Notes for agents

- Windows-first quickstart (README); on Linux/macOS the same commands apply with `python -m streamlit`.
- `.cognee/`, `token.json`, `credentials.json`, `.env` are gitignored — never commit them.
- The approval gate is a hard rule: never send email / create events without explicit human approval.
