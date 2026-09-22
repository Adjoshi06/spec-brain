"""Cognee smoke test: reset -> seed personal + office -> three recalls -> graph HTML.

    .venv\\Scripts\\python.exe smoke\\cognee_smoke.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import brain  # noqa: E402
import seed  # noqa: E402


def show(dataset: str, query: str, **kw) -> None:
    t0 = time.perf_counter()
    results = brain.recall_sync(dataset, query, **kw)
    dt = time.perf_counter() - t0
    print(f"\n=== recall({dataset!r}, {query!r}) -> {len(results)} result(s) in {dt:.1f}s")
    for i, r in enumerate(results):
        text = r["text"].replace("\n", " ")
        print(f"  [{i}] used={r['search_type_used']} kind={r['kind']} score={r['score']} marker={r.get('marker')}")
        print(f"      text: {text[:600]}")
        print(f"      evidence: {r['evidence'][:5]}")
    print("  formatted for LLM:\n   ", brain.format_recall(dataset, results).replace("\n", "\n    "))


def main() -> None:
    t_all = time.perf_counter()
    t0 = time.perf_counter()
    print("reset:", brain.reset_sync(), f"({time.perf_counter() - t0:.1f}s)")

    seed.seed_dataset("personal")
    seed.seed_dataset("office")

    show("personal", "What did I specify for the Mission St ceiling and why?")
    show("personal", "What did we decide about the Bayview flooring?")
    show("office", "What NRC is required in open office?")
    show("personal", "What did I specify for the Mission St ceiling and why?", search_type="CHUNKS", top_k=3)

    t0 = time.perf_counter()
    out = brain.visualize_sync("personal", str(brain.REPO_ROOT / "graph" / "personal.html"))
    print(f"\ngraph written: {out} ({time.perf_counter() - t0:.1f}s)")
    print(f"total {time.perf_counter() - t_all:.1f}s")


if __name__ == "__main__":
    main()
