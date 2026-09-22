"""Turn the real-time screen recording into a short time-lapse without ffmpeg filters:
extract frames, drop near-duplicates in Python, hold static stretches to at most one frame
every few seconds, and re-encode.

Usage: .venv\\Scripts\\python.exe timelapse.py [in.webm] [out.webm]
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent
IN = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "artifacts" / "video" / "spec-brain-demo-realtime.webm"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "artifacts" / "video" / "spec-brain-demo.webm"
FRAMES = ROOT / "out" / "frames"
KEPT = ROOT / "out" / "frames-kept"
SAMPLE_FPS = 4          # frames extracted per second of source (PNG: the bundled ffmpeg has no JPEG encoder)
OUT_FPS = int(os.environ.get("TL_FPS", "4"))                 # playback rate of kept frames
STATIC_HOLD_S = float(os.environ.get("TL_HOLD", "2.0"))       # while nothing changes, keep one frame every N s of source
CHANGE_THRESHOLD = float(os.environ.get("TL_THRESHOLD", "0.35"))  # mean abs pixel diff (0-255) on a grayscale thumbnail
THUMB = (192, 120)


def ffmpeg_path() -> str:
    base = Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"
    candidates = sorted(base.glob("ffmpeg-*/ffmpeg-win64.exe"))
    if not candidates:
        sys.exit("Playwright's ffmpeg not found; run: python -m playwright install")
    return str(candidates[-1])


def thumb(path: Path) -> Image.Image:
    with Image.open(path) as img:
        return img.convert("L").resize(THUMB)


def main() -> int:
    ff = ffmpeg_path()
    for folder in (FRAMES, KEPT):
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)

    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(IN), "-r", str(SAMPLE_FPS),
                    str(FRAMES / "%05d.png")], check=True)
    frames = sorted(FRAMES.glob("*.png"))
    print(f"extracted {len(frames)} frames at {SAMPLE_FPS} fps")

    kept = 0
    last_thumb = None
    last_kept_index = -10**9
    hold_frames = int(STATIC_HOLD_S * SAMPLE_FPS)
    for index, frame in enumerate(frames):
        current = thumb(frame)
        changed = True
        if last_thumb is not None:
            diff = ImageChops.difference(current, last_thumb)
            mean = sum(diff.getdata()) / (diff.width * diff.height)
            changed = mean > CHANGE_THRESHOLD
        if changed or index - last_kept_index >= hold_frames or index == len(frames) - 1:
            kept += 1
            shutil.copy(frame, KEPT / f"{kept:05d}.png")
            last_kept_index = index
            last_thumb = current
    print(f"kept {kept} frames -> {kept / OUT_FPS:.0f} s at {OUT_FPS} fps")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Feed raw RGB frames over stdin — the same path Playwright uses with this ffmpeg build.
    kept_frames = sorted(KEPT.glob("*.png"))
    with Image.open(kept_frames[0]) as first:
        width, height = first.size
    encoder = subprocess.Popen(
        [ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{width}x{height}", "-framerate", str(OUT_FPS), "-i", "-",
         "-c:v", "libvpx", "-b:v", "1500k", "-pix_fmt", "yuv420p", "-auto-alt-ref", "0", str(OUT)],
        stdin=subprocess.PIPE,
    )
    for frame in kept_frames:
        with Image.open(frame) as img:
            encoder.stdin.write(img.convert("RGB").tobytes())
    encoder.stdin.close()
    if encoder.wait() != 0:
        sys.exit(f"ffmpeg encode failed with {encoder.returncode}")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
