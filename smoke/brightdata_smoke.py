"""Smoke test: Bright Data hosted MCP — list tools, scrape the seed product pages, try one PDF.

Writes seed/public/cache/<slug>.md with a provenance header line. Run from the repo root:
    .venv\\Scripts\\python.exe smoke\\brightdata_smoke.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import web  # noqa: E402

SOURCES = ROOT / "seed" / "public" / "sources.json"
CACHE = ROOT / "seed" / "public" / "cache"
MAX_REQUESTS = 20


def markers(text: str) -> dict[str, bool]:
    low = text.lower()
    return {"NRC": "nrc" in low, "CAC": "cac" in low, "Class A": "class a" in low}


def first_url(search_text: str, domain_hint: str) -> str | None:
    urls = re.findall(r"https?://[^\s)\]>\"']+", search_text)
    for u in urls:
        if domain_hint in u and not u.lower().endswith((".png", ".jpg", ".svg")):
            return u
    return None


def main() -> None:
    requests_made = 0
    CACHE.mkdir(parents=True, exist_ok=True)
    entries = json.loads(SOURCES.read_text(encoding="utf-8"))

    t0 = time.time()
    tools = web.list_tools()
    requests_made += 1
    print(f"tools ({time.time() - t0:.1f}s): {tools}")

    latencies: list[float] = []
    for entry in entries:
        url, slug = entry["url"], entry["slug"]
        text, used_url, note = "", url, ""
        for attempt in (1, 2):
            if requests_made >= MAX_REQUESTS:
                note = "request budget exhausted"
                break
            t0 = time.time()
            try:
                text = web.scrape_markdown(used_url)
                requests_made += 1
                latencies.append(time.time() - t0)
                if len(text) > 500:
                    break
                note = f"attempt {attempt}: only {len(text)} chars"
            except Exception as exc:  # noqa: BLE001
                requests_made += 1
                latencies.append(time.time() - t0)
                note = f"attempt {attempt}: {str(exc)[:160]}"
                text = ""
        if len(text) <= 500 and requests_made < MAX_REQUESTS:
            try:
                found = web.search(f"{entry['product']} NRC CAC datasheet")
                requests_made += 1
                domain = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
                alt = first_url(found, domain)
                note += f" | search alt: {alt}"
                if alt and alt != url and requests_made < MAX_REQUESTS:
                    t0 = time.time()
                    text = web.scrape_markdown(alt)
                    requests_made += 1
                    latencies.append(time.time() - t0)
                    used_url = alt
            except Exception as exc:  # noqa: BLE001
                note += f" | search failed: {str(exc)[:120]}"
        m = markers(text)
        secs = latencies[-1] if latencies else 0.0
        print(f"{slug:28s} {secs:6.1f}s {len(text):7d} chars  NRC={m['NRC']} CAC={m['CAC']} ClassA={m['Class A']}  {note}")
        if text:
            header = (
                f"<!-- source_url: {used_url} | retrieved_at: {datetime.now(timezone.utc).isoformat()} "
                f"| product: {entry['product']} | manufacturer: {entry['manufacturer']} -->"
            )
            (CACHE / f"{slug}.md").write_text(header + "\n" + text, encoding="utf-8")

    if latencies:
        print(f"average scrape latency: {sum(latencies) / len(latencies):.1f}s over {len(latencies)} calls")

    pdf_entry = next((e for e in entries if e.get("datasheet_pdf")), None)
    if pdf_entry and requests_made < MAX_REQUESTS:
        t0 = time.time()
        try:
            pdf_text = web.fetch_pdf_text(pdf_entry["datasheet_pdf"])
            print(f"PDF REST OK ({time.time() - t0:.1f}s): {len(pdf_text)} chars from {pdf_entry['slug']} datasheet; NRC={'nrc' in pdf_text.lower()}")
        except Exception as exc:  # noqa: BLE001
            print(f"PDF REST FAILED ({time.time() - t0:.1f}s): {str(exc)[:400]}")
    print(f"requests made: {requests_made}")


if __name__ == "__main__":
    main()
