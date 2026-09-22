"""Exercise the agent's tool wrappers directly, without the model. Does not touch Cognee."""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("SPEC_BRAIN_QUIET", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agent  # noqa: E402

print("== inbox_scan ==")
print(agent.inbox_scan(query='subject:"Mission St" Sonar lead time')[:700])

print("\n== live_lookup (one Bright Data fetch) ==")
out = agent.live_lookup(url="https://www.usg.com/en-US/p/product/mars-high-nrc-acoustical-panels-88137")
print(out[:400])
print("... total chars:", len(out))
print("mentions NRC:", bool(re.search("nrc", out, re.I)), "CAC:", bool(re.search("cac", out, re.I)),
      "Class A:", bool(re.search("class a", out, re.I)))

print("\n== check_substitute (sandbox) ==")
print(agent.check_substitute(
    requirements={"nrc_min": 0.85, "fire_classes": ["Class A"], "size": "24x24", "recycled_min": 0.30},
    candidate={"nrc": 0.95, "fire_class": "Class A", "size": "2' x 2'", "recycled": None},
    candidate_name="USG Mars High-NRC (values from live page)",
))
