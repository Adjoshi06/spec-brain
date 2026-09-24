# Codebase Map — spec-brain

Flat single-app Python repo. Depth cap 2; entry points bolded.

| Path | What |
|---|---|
| `agent.py` | Strands agent: twelve tools, system prompt, approval-gate wiring (imports `brain`, `web`, `google_io`, `spec_check`, `sandbox`) |
| `brain.py` | Cognee wrapper — remember / recall / visualize on one event loop, three hard-walled datasets |
| `seed.py` | Seeds the three Cognee layers from `seed/` and writes `graph/*.html` |
| `spec_check.py` | Deterministic substitution check (pass/fail as code); unit-tested in `tests/` |
| `sandbox.py` | Locked-down Docker runner (no network, read-only, caps dropped) for the check |
| `web.py` | Bright Data hosted Web MCP client (scrape, search) |
| `google_io.py` | Gmail / Drive / Calendar clients with local-file fallbacks |
| `ui.py` | Streamlit browser UI — demo beats, tool-call trace, Approve/Deny panel |
| `cli.py` | Rich terminal UI (interactive session) |
| `demo.py` | Scripted five-beat run → `out/demo-transcript.md` |
| `make_video.py` / `timelapse.py` / `clean_cache.py` | Demo-video capture and cache hygiene helpers |
| `prep.ps1` | Windows prep script (venv + install) |
| `tests/` | pytest suite for the deterministic check (12 tests) |
| `smoke/` | One runnable check per integration (brightdata, google, cognee, calendar, tools, after-beat, send trigger) |
| `seed/` | Fictional persona data: personal notes, office standard, Drive note, cached public pages |
| `graph/` | Pre-generated Cognee graph visualizations (`personal/office/public.html`) |
| `artifacts/` | Run evidence: transcript, smoke results, generated request, demo video |
| `personal_data/` | One sample .eml used by the demo |
