"""Collapse the Bright Data security wrapper in already-cached scrapes (seed/public/cache)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from web import strip_untrusted_wrapper  # noqa: E402

CACHE = Path(__file__).resolve().parent / "seed" / "public" / "cache"

for path in sorted(CACHE.glob("*.md")):
    header, _, body = path.read_text(encoding="utf-8").partition("\n")
    cleaned = strip_untrusted_wrapper(body)
    path.write_text(f"{header}\n{cleaned}\n", encoding="utf-8")
    print(f"{path.name}: {len(body)} -> {len(cleaned)} chars")
