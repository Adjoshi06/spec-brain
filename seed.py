"""Seed the three Spec Brain datasets from ./seed.

  seed/personal/*.md        -> dataset "personal" (node set from frontmatter)
  seed/office/standard.md   -> dataset "office"   (node set "standard")
  seed/public/cache/*.md    -> dataset "public"   (node set "datasheet"; written by the web workstream)

Idempotent: cognee de-duplicates by content hash.

    python seed.py [--reset] [--only personal|office|public] [--visualize]
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import brain

SEED_DIR = brain.REPO_ROOT / "seed"
GRAPH_DIR = brain.REPO_ROOT / "graph"
PLACEHOLDER_EMAIL = "contractor@example.com"


def parse_note(path: Path) -> tuple[dict, str]:
    """Split a ``---`` frontmatter block (key: value lines) from the body."""
    raw = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = raw
    if raw.lstrip().startswith("---"):
        parts = raw.lstrip().split("---", 2)
        if len(parts) == 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    meta[key.strip()] = val.strip()
            body = parts[2]
    return meta, body.strip()


def _contractor_email() -> str:
    email = os.environ.get("CONTRACTOR_EMAIL", "").strip()
    if not email:
        print(f"WARNING: CONTRACTOR_EMAIL not set; using {PLACEHOLDER_EMAIL}", file=sys.stderr)
        return PLACEHOLDER_EMAIL
    return email


def load_notes(dataset: str) -> list[tuple[str, str, str]]:
    """Return (node_set, label, text) triples for a dataset, header line prepended."""
    if dataset == "personal":
        files = sorted((SEED_DIR / "personal").glob("*.md"))
        default_ns = "note"
    elif dataset == "office":
        files = [SEED_DIR / "office" / "standard.md"]
        default_ns = "standard"
    elif dataset == "public":
        files = sorted((SEED_DIR / "public" / "cache").glob("*.md"))
        return [("datasheet", f.stem, f.read_text(encoding="utf-8").strip()) for f in files]
    else:
        raise ValueError(dataset)

    email = _contractor_email()
    out = []
    for f in files:
        meta, body = parse_note(f)
        node_set = meta.get("node_set", default_ns)
        date = meta.get("date", "undated")
        text = f"[{dataset} {node_set}, {date}] " + body.replace("{CONTRACTOR_EMAIL}", email)
        out.append((node_set, f.stem, text))
    return out


def seed_dataset(dataset: str) -> list[dict]:
    """Remember every note for one dataset. One cognee call per node set (fewer pipeline runs)."""
    notes = load_notes(dataset)
    if not notes:
        print(f"[{dataset}] nothing to seed")
        return []
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for node_set, label, text in notes:
        groups[node_set].append((label, text))

    reports = []
    for node_set, items in groups.items():
        t0 = time.perf_counter()
        # A list of DataItems goes through one pipeline run; labels stay per item.
        from cognee.tasks.ingestion.data_item import DataItem  # local import: brain already configured cognee

        async def _remember_group(items=items, node_set=node_set):
            import cognee

            async with brain._lock:
                result = await cognee.remember(
                    [DataItem(data=text, label=label) for label, text in items],
                    dataset_name=dataset,
                    node_set=[node_set],
                    self_improvement=False,
                )
            if getattr(result, "status", None) == "errored":
                raise RuntimeError(f"remember failed for {dataset}/{node_set}: {result.error}")
            return getattr(result, "status", None)

        status = brain._run(_remember_group(), timeout=900)
        elapsed = round(time.perf_counter() - t0, 1)
        labels = [label for label, _ in items]
        print(f"[{dataset}] node_set={node_set:<10} {len(items)} item(s) {elapsed:>6}s status={status} {labels}")
        reports.append({"dataset": dataset, "node_set": node_set, "items": labels, "elapsed": elapsed, "status": status})
    return reports


def seed_all(only: str | None = None, reset: bool = False, visualize: bool = False) -> list[dict]:
    t_all = time.perf_counter()
    if reset:
        t0 = time.perf_counter()
        print("reset:", brain.reset_sync(), f"({time.perf_counter() - t0:.1f}s)")
    datasets = [only] if only else list(brain.DATASETS)
    reports = []
    for ds in datasets:
        reports.extend(seed_dataset(ds))
    if visualize:
        for ds in datasets:
            if any(r["dataset"] == ds for r in reports):
                t0 = time.perf_counter()
                path = brain.visualize_sync(ds, str(GRAPH_DIR / f"{ds}.html"))
                print(f"[{ds}] graph -> {path} ({time.perf_counter() - t0:.1f}s)")
    print(f"total {time.perf_counter() - t_all:.1f}s")
    return reports


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reset", action="store_true", help="forget everything first")
    ap.add_argument("--only", choices=brain.DATASETS, help="seed just one dataset")
    ap.add_argument("--visualize", action="store_true", help="write graph/<dataset>.html")
    args = ap.parse_args()
    seed_all(only=args.only, reset=args.reset, visualize=args.visualize)


if __name__ == "__main__":
    main()
