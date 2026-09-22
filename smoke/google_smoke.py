"""Smoke test for google_io: local fallback first, then live Gmail/Drive once credentials.json exists.

Usage:  .venv\\Scripts\\python.exe smoke\\google_smoke.py [--send-test] [--no-wait]
"""

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

import google_io  # noqa: E402

load_dotenv(ROOT / ".env")

SEND_TEST = "--send-test" in sys.argv
NO_WAIT = "--no-wait" in sys.argv


def banner(text: str) -> None:
    print("\n" + "=" * 78 + f"\n{text}\n" + "=" * 78)


def show_hits(hits: list[dict]) -> None:
    if not hits:
        print("  (no hits)")
    for h in hits:
        print(f"  [{h['source']}] from={h['from']!r} subject={h['subject']!r} date={h['date']!r}")
        print(f"     body: {h['body_text'][:200]!r}")


banner("1) LOCAL FALLBACK (personal_data/*.eml, no credentials needed)")
hits = google_io._search_local('subject:"Mission St" Sonar lead time', 5)
show_hits(hits)
assert hits, "fallback found nothing in personal_data/"
assert "16 weeks" in hits[0]["body_text"], "sample .eml body did not parse"
print("  fallback search OK")
if not google_io.google_available():
    out = google_io._send_local("demo@example.com", "[Spec Brain fallback test]", "fallback body")
    print(f"  fallback send wrote {out['id']}")

banner("2) LIVE GOOGLE (needs credentials.json in repo root)")
deadline = time.time() + 15 * 60
while not google_io.google_available():
    if NO_WAIT:
        print("  credentials.json absent; --no-wait given, stopping here.")
        sys.exit(0)
    remaining = int(deadline - time.time())
    if remaining <= 0:
        print("  credentials.json never appeared within 15 minutes; live test skipped.")
        sys.exit(0)
    print(f"  waiting for {google_io.CREDENTIALS_FILE.name} ... ({remaining // 60}m{remaining % 60:02d}s left)")
    time.sleep(20)

try:
    print("\n  >>> A BROWSER TAB WILL OPEN: sign in and APPROVE the consent screen (Gmail read/send + Drive read). <<<\n")
    gmail, drive = google_io.get_services()
    profile = gmail.users().getProfile(userId="me").execute()
    print(f"  authorised as {profile.get('emailAddress')} (token cached in token.json)")

    print("\n  inbox search: subject:\"Mission St\"")
    show_hits(google_io.search_inbox('subject:"Mission St"', 5))

    print("\n  drive listing (5 most recent):")
    for f in google_io.list_drive_files("", 5):
        print(f"  [{f['source']}] {f['name']}  {f['mimeType']}  {f['modifiedTime']}  {f.get('webViewLink', '')}")

    if SEND_TEST:
        to = os.environ.get("CONTRACTOR_EMAIL") or profile.get("emailAddress")
        sent = google_io.send_email(to, "[Spec Brain test]", "Spec Brain smoke test: Gmail send works.")
        print(f"\n  sent test email to {to}: id={sent['id']} threadId={sent.get('threadId')}")
    else:
        print("\n  (send skipped; run with --send-test to send to CONTRACTOR_EMAIL)")
except Exception as exc:  # readable diagnostics for the common OAuth failures
    from googleapiclient.errors import HttpError

    text = str(exc)
    if "access_denied" in text:
        print("  access_denied: the consent screen is in Testing mode; add this Google account as a test user.")
    elif "invalid_grant" in text:
        print("  invalid_grant: token.json is stale; delete it and re-run.")
    elif "accessNotConfigured" in text or "has not been used in project" in text:
        print("  API not enabled: enable the Gmail API and Drive API in the Google Cloud project, then re-run.")
    elif isinstance(exc, HttpError):
        print(f"  Google API error {exc.status_code}: {exc.reason}")
    else:
        print(f"  {type(exc).__name__}: {text}")
    sys.exit(1)
