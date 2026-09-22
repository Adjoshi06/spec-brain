"""Send the demo trigger email (the rep's 16-week note) from the authorised account to the
address in CONTRACTOR_EMAIL (your own inbox), then confirm the inbox tool can find it.

Approved by the user before running. Sends exactly one email.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
os.environ.setdefault("SPEC_BRAIN_QUIET", "1")
sys.path.insert(0, str(ROOT))

import agent  # noqa: E402
import google_io  # noqa: E402

TO = os.environ.get("CONTRACTOR_EMAIL", "").strip()
SUBJECT = "Mission St — Rockfon Sonar lead time update"
BODY = ("Hi — heads-up on the Sonar 2x2 lay-in for Mission St: because of plant maintenance the lead "
        "time is now 16 weeks from PO, not 6. Happy to walk through alternatives.\n\n— Sam (demo rep)\n\n"
        "(demo data: fictional rep, sent to myself for the Spec Brain hackathon demo)")

if not TO:
    sys.exit("CONTRACTOR_EMAIL is not set in .env")
if not google_io.google_ready():
    sys.exit("Google is not ready (credentials.json + token.json required)")

sent = google_io.send_email(TO, SUBJECT, BODY)
print("send result:", sent)
if not str(sent.get("source", "")).startswith("gmail"):
    sys.exit("Send fell back to a local file — Gmail API not usable yet")

for attempt in range(6):
    time.sleep(5)
    out = agent.inbox_scan(query='subject:"Mission St" newer_than:1d')
    if "[INBOX · gmail]" in out:
        print(f"inbox tool found it after {(attempt + 1) * 5}s:\n{out[:600]}")
        break
    print(f"attempt {attempt + 1}: not indexed yet")
else:
    sys.exit("Sent, but the inbox tool did not find the message within 30s")
