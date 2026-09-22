"""Spec Brain memory layer on cognee 1.6.0.

Three hard-walled datasets (``personal`` / ``office`` / ``public``). Every recall is pinned to
exactly one dataset, so layers never mix and every fact can be labeled with where it came from.

All cognee work runs on ONE long-lived background event loop thread. Strands tool functions run
in worker threads, so they call the ``*_sync`` wrappers; async code can await the coroutines
directly (from that same loop). A module lock serializes cognee calls because the Ladybug graph
store takes exclusive file locks.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent
load_dotenv(REPO_ROOT / ".env", override=False)

# Storage must be configured through the environment BEFORE cognee is imported: BaseConfig is a
# pydantic BaseSettings read once (lru_cache) and its defaults point inside site-packages.
_COGNEE_DIR = REPO_ROOT / ".cognee"
os.environ.setdefault("DATA_ROOT_DIRECTORY", (_COGNEE_DIR / "data").as_posix())
os.environ.setdefault("SYSTEM_ROOT_DIRECTORY", (_COGNEE_DIR / "system").as_posix())
os.environ.setdefault("CACHE_ROOT_DIRECTORY", (_COGNEE_DIR / "cache").as_posix())
os.environ.setdefault("TELEMETRY_DISABLED", "true")
for _d in ("DATA_ROOT_DIRECTORY", "SYSTEM_ROOT_DIRECTORY", "CACHE_ROOT_DIRECTORY"):
    Path(os.environ[_d]).mkdir(parents=True, exist_ok=True)

import cognee  # noqa: E402
from cognee import SearchType  # noqa: E402
from cognee.tasks.ingestion.data_item import DataItem  # noqa: E402

# Belt and braces: apply the same paths programmatically.
cognee.config.data_root_directory(os.environ["DATA_ROOT_DIRECTORY"])
cognee.config.system_root_directory(os.environ["SYSTEM_ROOT_DIRECTORY"])

log = logging.getLogger("spec_brain.brain")

DATASETS = ("personal", "office", "public")
LAYER_LABELS = {"personal": "PERSONAL", "office": "OFFICE STANDARD", "public": "PUBLIC"}

_lock = asyncio.Lock()


def _check_dataset(dataset: str) -> None:
    if dataset not in DATASETS:
        raise ValueError(f"unknown dataset {dataset!r}; expected one of {DATASETS}")


# --------------------------------------------------------------------------- async API


async def remember(
    dataset: str,
    text: str,
    node_set: list[str] | None = None,
    label: str | None = None,
    self_improvement: bool = False,
) -> dict:
    """Store ``text`` in ``dataset`` (add + cognify). Returns a small status dict.

    For ``public`` the caller must already have put the source URL and retrieval date inside
    ``text`` so citations carry them. cognee de-duplicates by content hash, so re-remembering
    the same text is a cheap no-op.
    """
    _check_dataset(dataset)
    item = DataItem(data=text, label=label)
    kwargs: dict[str, Any] = {"dataset_name": dataset, "self_improvement": self_improvement}
    if node_set:
        kwargs["node_set"] = list(node_set)
    t0 = time.perf_counter()
    async with _lock:
        result = await cognee.remember(item, **kwargs)
    status = getattr(result, "status", None)
    if status == "errored":
        raise RuntimeError(f"cognee.remember failed for {dataset}/{label}: {getattr(result, 'error', '?')}")
    return {
        "status": status,
        "dataset": dataset,
        "label": label,
        "node_set": node_set or [],
        "elapsed": round(time.perf_counter() - t0, 1),
        "items_processed": getattr(result, "items_processed", None),
    }


def _evidence_from(metadata: dict, raw: Any) -> list[str]:
    out: list[str] = []
    for key in ("evidence", "references", "sources"):
        val = metadata.get(key)
        if isinstance(val, list):
            out.extend(_ev_str(v) for v in val)
        elif val:
            out.append(_ev_str(val))
    for key in ("document_name", "document", "source_url", "name", "doc_id", "chunk_id"):
        if metadata.get(key):
            out.append(f"{key}={metadata[key]}")
    if isinstance(raw, dict):
        for key in ("document_name", "source_url"):
            if raw.get(key) and f"{key}={raw[key]}" not in out:
                out.append(f"{key}={raw[key]}")
    return out


def _ev_str(v: Any) -> str:
    if isinstance(v, dict):
        keep = {k: v[k] for k in ("document_name", "document", "name", "chunk_id", "source_url", "text") if k in v}
        if "text" in keep:
            keep["text"] = str(keep["text"])[:160]
        return ", ".join(f"{k}={val}" for k, val in keep.items()) or str(v)[:200]
    return str(v)[:200]


def _to_dict(r: Any, dataset: str, used: SearchType) -> dict:
    metadata = dict(getattr(r, "metadata", None) or {})
    raw = getattr(r, "raw", None)
    d = {
        "text": getattr(r, "text", "") or "",
        "dataset": getattr(r, "dataset_name", None) or dataset,
        "layer": LAYER_LABELS[dataset],
        "score": getattr(r, "score", None),
        "evidence": _evidence_from(metadata, raw),
        "search_type_used": used.value,
        "source": getattr(r, "source", None),
        "kind": getattr(r, "kind", None),
        "raw": r.model_dump() if hasattr(r, "model_dump") else raw,
    }
    if d["source"] == "system":  # ResponseMarkerEntry: "memory warming up" / "build failed"
        d["marker"] = getattr(r, "status", None)
    return d


async def recall(
    dataset: str,
    query: str,
    top_k: int = 8,
    search_type: str = "GRAPH_COMPLETION",
    timeout: float = 90.0,
) -> list[dict]:
    """Search ONE dataset. Tries ``search_type``; on error/timeout falls back to CHUNKS (no LLM).

    Each dict: text, dataset, layer, score, evidence (list[str]), search_type_used, source,
    kind, raw, and ``marker`` when cognee returned a system marker instead of data.
    """
    _check_dataset(dataset)
    requested = SearchType[search_type]
    used = requested

    async def _do(st: SearchType) -> list:
        return await asyncio.wait_for(
            cognee.recall(query, st, datasets=[dataset], top_k=top_k, include_references=True),
            timeout,
        )

    async with _lock:
        try:
            results = await _do(requested)
        except Exception as error:  # noqa: BLE001 - we translate everything into a fallback
            if type(error).__name__ == "DatasetNotFoundError":
                log.info("recall(%s): dataset does not exist yet -> []", dataset)
                return []
            if requested == SearchType.CHUNKS:
                raise
            log.warning("recall(%s) %s failed (%s); falling back to CHUNKS", dataset, requested.value, error)
            used = SearchType.CHUNKS
            try:
                results = await _do(SearchType.CHUNKS)
            except Exception as error2:  # noqa: BLE001
                if type(error2).__name__ == "DatasetNotFoundError":
                    return []
                raise
    return [_to_dict(r, dataset, used) for r in (results or [])]


async def visualize(dataset: str, out_path: str, query: str | None = None) -> str:
    """Render the dataset graph to a self-contained HTML file. ``query`` highlights a subgraph."""
    _check_dataset(dataset)
    target = Path(out_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    async with _lock:
        await cognee.visualize_graph(
            destination_file_path=str(target), dataset=dataset, full=query is None, query=query
        )
    return str(target)


async def reset() -> dict:
    """Forget everything (all datasets). Falls back to prune if the DB was never created."""
    async with _lock:
        try:
            summary = await cognee.forget(everything=True)
            return {"forgot": summary}
        except Exception as error:  # noqa: BLE001
            log.warning("forget(everything=True) failed (%s); pruning instead", error)
            await cognee.prune.prune_data()
            await cognee.prune.prune_system(metadata=True)
            return {"pruned": True, "reason": repr(error)}


# --------------------------------------------------------------------------- sync wrappers

_loop: asyncio.AbstractEventLoop | None = None
_loop_guard = threading.Lock()


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    with _loop_guard:
        if _loop is None:
            loop = asyncio.new_event_loop()
            threading.Thread(target=loop.run_forever, name="cognee-loop", daemon=True).start()
            _loop = loop
    return _loop


def _run(coro, timeout: float):
    return asyncio.run_coroutine_threadsafe(coro, _get_loop()).result(timeout=timeout)


def remember_sync(dataset: str, text: str, node_set: list[str] | None = None, label: str | None = None,
                  self_improvement: bool = False, timeout: float = 900.0) -> dict:
    return _run(remember(dataset, text, node_set=node_set, label=label, self_improvement=self_improvement), timeout)


def recall_sync(dataset: str, query: str, top_k: int = 8, search_type: str = "GRAPH_COMPLETION",
                timeout: float = 180.0) -> list[dict]:
    return _run(recall(dataset, query, top_k=top_k, search_type=search_type, timeout=max(timeout - 5, 10)), timeout)


def visualize_sync(dataset: str, out_path: str, query: str | None = None, timeout: float = 300.0) -> str:
    return _run(visualize(dataset, out_path, query=query), timeout)


def reset_sync(timeout: float = 300.0) -> dict:
    return _run(reset(), timeout)


# --------------------------------------------------------------------------- rendering helper


def format_recall(dataset: str, results: list[dict], max_chars: int = 1200) -> str:
    """Render recall results as labeled lines for an LLM tool result. Empty -> explicit unknown."""
    label = LAYER_LABELS[dataset]
    if not results:
        return f"[{label}] nothing stored about this. Treat as unknown."
    lines = []
    for r in results:
        if r.get("marker"):
            lines.append(f"[{label}] (system) {r['text']}")
            continue
        text = r["text"].strip().replace("\n", " ")
        if len(text) > max_chars:
            text = text[: max_chars - 3] + "..."
        ev = f" | evidence: {'; '.join(r['evidence'][:4])}" if r.get("evidence") else ""
        lines.append(f"[{label}] {text}{ev}")
    return "\n".join(lines)
