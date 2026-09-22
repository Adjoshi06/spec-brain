"""Read-only check of the Calendar scope: list the next few events. Creates nothing."""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import google_io  # noqa: E402

if not google_io.google_ready():
    sys.exit("Google is not ready (credentials.json + token.json required)")

calendar = google_io.get_calendar()
now = dt.datetime.now(dt.timezone.utc).isoformat()
listing = calendar.events().list(calendarId="primary", timeMin=now, maxResults=5, singleEvents=True,
                                 orderBy="startTime").execute()
items = listing.get("items", [])
print(f"calendar scope OK — {len(items)} upcoming event(s)")
for event in items:
    start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
    print(f"  {start}  {event.get('summary', '(no title)')}")
