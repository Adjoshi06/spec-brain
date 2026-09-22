"""Record a demo video of the live UI: drives the Streamlit app in headless Chromium, clicks the
beats in order, approves the gated actions, and saves artifacts/video/spec-brain-demo.webm.

Usage: .venv\\Scripts\\python.exe make_video.py [--beats "1 · Before,2 · Inbox,..."] [--no-reset]
The UI must already be running on http://localhost:8501 and nobody else should click it meanwhile.
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
VIDEO_DIR = ROOT / "artifacts" / "video"
URL = "http://localhost:8501"
DEFAULT_BEATS = ["1 · Before", "2 · Inbox", "2b · Site meeting (Drive)", "3 · Substitute",
                 "4 · Send", "4b · Reminder", "5 · After"]
TURN_TIMEOUT_S = 300


def wait_until_idle(page, probe_button: str, timeout_s: float = TURN_TIMEOUT_S) -> None:
    """Beat buttons are disabled while a turn runs; scroll to the bottom until they re-enable."""
    started = time.time()
    button = page.get_by_role("button", name=probe_button, exact=True)
    while time.time() - started < timeout_s:
        page.mouse.wheel(0, 20000)
        try:
            if button.is_enabled():
                time.sleep(1.5)
                page.mouse.wheel(0, 20000)
                return
        except PlaywrightTimeout:
            pass
        time.sleep(1.0)
    raise RuntimeError(f"turn did not finish within {timeout_s}s")


def approve_if_asked(page, timeout_s: float = 120) -> bool:
    approve = page.get_by_role("button", name="✅ Approve", exact=True)
    started = time.time()
    while time.time() - started < timeout_s:
        page.mouse.wheel(0, 20000)
        if approve.count() and approve.first.is_visible():
            time.sleep(2.5)  # let the audience read the draft
            approve.first.click()
            return True
        time.sleep(1.0)
    return False


def main(argv) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--beats", default=",".join(DEFAULT_BEATS))
    parser.add_argument("--no-reset", action="store_true", help="do not clear/reset memory afterwards")
    args = parser.parse_args(argv)
    beats = [b.strip() for b in args.beats.split(",") if b.strip()]

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    for old in VIDEO_DIR.glob("*.webm"):
        old.unlink()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)

        # Unrecorded prep: clear any rehearsal conversation and rebuild a clean memory so the
        # "before" beat honestly has no decision on record.
        prep = browser.new_page(viewport={"width": 1440, "height": 900})
        prep.goto(URL, wait_until="load")
        clear_btn = prep.get_by_role("button", name="Clear conversation (keep memory)", exact=True)
        clear_btn.wait_for(timeout=60000)
        if clear_btn.is_enabled():
            clear_btn.click()
            time.sleep(3)
        if not args.no_reset:
            print("prep: reset memory (~70 s, not recorded)", flush=True)
            prep.get_by_role("button", name="↺ Reset memory (clean 'before' state, ~70 s)", exact=True).click()
            time.sleep(5)
            wait_until_idle(prep, beats[0], timeout_s=300)
        prep.close()

        context = browser.new_context(viewport={"width": 1440, "height": 900},
                                      record_video_dir=str(VIDEO_DIR),
                                      record_video_size={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(URL, wait_until="load")
        page.get_by_role("button", name=beats[0], exact=True).wait_for(timeout=60000)
        time.sleep(3)  # title card

        for beat in beats:
            print(f"beat: {beat}", flush=True)
            page.get_by_role("button", name=beat, exact=True).click()
            time.sleep(1.0)
            probe = beats[0]
            # a gated beat pauses for approval before the buttons re-enable
            if beat.startswith("4"):
                if approve_if_asked(page):
                    print("  approved", flush=True)
            wait_until_idle(page, probe)
            time.sleep(2.5)  # dwell on the answer

        time.sleep(4)
        video = page.video
        context.close()  # flushes the recording
        path = Path(video.path())
        target = VIDEO_DIR / "spec-brain-demo.webm"
        shutil.move(str(path), str(target))
        print(f"video: {target} ({target.stat().st_size / 1e6:.1f} MB)", flush=True)

        if not args.no_reset:
            print("restoring clean state: clear conversation + reset memory", flush=True)
            page2 = browser.new_page(viewport={"width": 1440, "height": 900})
            page2.goto(URL, wait_until="load")
            page2.get_by_role("button", name="Clear conversation (keep memory)", exact=True).wait_for(timeout=60000)
            page2.get_by_role("button", name="Clear conversation (keep memory)", exact=True).click()
            time.sleep(3)
            page2.get_by_role("button", name="↺ Reset memory (clean 'before' state, ~70 s)", exact=True).click()
            started = time.time()
            reset_button = page2.get_by_role("button", name="1 · Before", exact=True)
            while time.time() - started < 240:
                try:
                    if reset_button.is_enabled():
                        break
                except PlaywrightTimeout:
                    pass
                time.sleep(2)
            print("memory reset done", flush=True)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
