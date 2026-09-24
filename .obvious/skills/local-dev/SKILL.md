---
name: local-dev
description: How to get spec-brain running locally, learned during onboarding (2026-09-24)
---

## Environment

- System Python 3.13 works even though the README quickstart targets 3.12 (cognee 1.6.0 + strands
  installed cleanly). No venv required in the sandbox; `pip install -r requirements.txt streamlit`.
- **No Docker daemon** in the sandbox. `spec_check.check_substitute` still works when called as a
  library (that is what the tests do); the in-container sandboxed mode of the agent tool does not run.
- No real API keys available onboarding-time: `secrets` flow not exposed for this repo. Write
  `.env` from `.env.example` with clearly-named dummy values and local Cognee paths
  (`/home/user/work/spec-brain/.cognee/{data,system}`); replace the Windows `C:/...` defaults.

## Startup

- `python -m streamlit run ui.py --server.headless true` — run under tmux/nohup with ALL output
  redirected; a bare `&` keeps the exec stream open and times the command out.
- Port is dynamic: when 8501 was busy (stale process), Streamlit took **8502**. Always parse
  `Local URL:` from `/tmp/streamlit.log`. Verify `curl -s http://localhost:PORT/_stcore/health`.

## Verification (what worked without real keys)

1. `python -m pytest tests/ -q` → 12 passed.
2. Streamlit serves HTTP 200 on the parsed port; `/_stcore/health` → 200.
3. `check_substitute` one-liner → verdict PASS.

## What does NOT work without real credentials

Agent chat (Anthropic), `seed.py` Cognee build (OpenAI), Bright Data scrapes, Gmail/Drive/Calendar I/O,
`demo.py`. `smoke/google_smoke.py` needs OAuth consent and `credentials.json` (gitignored).
