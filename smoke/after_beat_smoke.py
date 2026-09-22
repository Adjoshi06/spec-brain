"""Verify the write-back beat: a stored decision must come back from recall_personal.

Usage: python smoke\after_beat_smoke.py            # recall only (decision already stored)
       python smoke\after_beat_smoke.py --remember # store a test decision first (pollutes memory;
                                                   # run seed.py --reset afterwards)
"""

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("SPEC_BRAIN_QUIET", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent  # noqa: E402
import brain  # noqa: E402

QUERY = "Mission St ceiling substitution decision USG Mars High-NRC"

if "--remember" in sys.argv:
    text = ("[personal decision, 2026-09-21] TEST: substitute for the Mission St Level 3 ceiling is USG Mars "
            "High-NRC 2x2 lay-in, 0.85 NRC / 35 CAC configuration; passed the office standard in the sandboxed "
            "check; substitution request sent to the BuildCo PM; lead time still to be confirmed in writing.")
    started = time.perf_counter()
    brain.remember_sync("personal", text, node_set=["decision"])
    print(f"remember took {time.perf_counter() - started:.1f}s")

started = time.perf_counter()
out = agent.recall_personal(query=QUERY)
print(f"recall took {time.perf_counter() - started:.1f}s")
print(out[:2500])
found = "USG Mars" in out and "decision" in out.lower()
print("\nAFTER-BEAT:", "OK — decision retrievable" if found else "FAIL — decision not found in recall")
sys.exit(0 if found else 1)
