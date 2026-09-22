"""Gmail + Google Drive access for Spec Brain, with a local-file fallback.

Every function returns dicts that carry a ``source`` key (``"gmail"``, ``"drive"`` or
``"local_file"``) so the agent can label on screen where personal data came from.

Live mode needs ``credentials.json`` (an OAuth *Desktop app* client) next to this file.
The first call opens a browser for consent and caches the token in ``token.json``.
Without ``credentials.json`` the inbox is read from ``personal_data/*.eml|*.txt`` and
outgoing mail is written to ``out/<timestamp>-request.md``.
"""

from __future__ import annotations

import base64
import email
import email.policy
import html
import io
import os
import re
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.readonly",
]

ROOT = Path(__file__).resolve().parent
CREDENTIALS_FILE = ROOT / "credentials.json"
TOKEN_FILE = ROOT / "token.json"
PERSONAL_DATA_DIR = ROOT / "personal_data"
OUT_DIR = ROOT / "out"

GOOGLE_DOC = "application/vnd.google-apps.document"
_TEXT_MIMES = {"text/plain", "text/markdown", "text/x-markdown", "text/csv", "application/json"}


def google_available() -> bool:
    """True when an OAuth client file is present, i.e. live Gmail/Drive can be used."""
    return CREDENTIALS_FILE.exists()


def google_ready() -> bool:
    """True when live Google can be used WITHOUT opening a browser: client file plus a cached
    token (created once by smoke/google_smoke.py). The agent tools use this so a demo never
    blocks on a consent tab; set GOOGLE_FORCE_LIVE=1 to override."""
    if os.environ.get("GOOGLE_FORCE_LIVE") == "1":
        return CREDENTIALS_FILE.exists()
    return CREDENTIALS_FILE.exists() and TOKEN_FILE.exists()


# --------------------------------------------------------------------------- auth

def _load_credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and not set(SCOPES).issubset(set(creds.scopes or [])):
            creds = None  # token was minted for different scopes; re-consent
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:  # refresh token revoked/expired -> fall through to consent
            creds = None
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
        # Fixed port: the OAuth client is a "web" type, so http://localhost:<port>/ must be
        # registered as an authorised redirect URI in the Google Cloud console.
        port = int(os.environ.get("GOOGLE_OAUTH_PORT", "8765"))
        creds = flow.run_local_server(port=port, open_browser=True, timeout_seconds=600)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


_services: tuple | None = None


def _reset_services() -> None:
    """Drop cached API clients so the next call rebuilds them from the token file (e.g. after
    an expired access token failed to refresh inside a long-running process)."""
    global _services, _calendar
    _services = None
    _calendar = None


def get_services():
    """Return ``(gmail_service, drive_service)``; runs the OAuth flow on first use."""
    global _services
    if _services is None:
        from googleapiclient.discovery import build

        creds = _load_credentials()
        gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        _services = (gmail, drive)
    return _services


# --------------------------------------------------------------------------- helpers

def _b64url_decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("ascii") + b"=" * (-len(data) % 4)).decode("utf-8", "replace")


def _strip_html(text: str) -> str:
    text = re.sub(r"<(script|style).*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>|</p>|</div>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", html.unescape(text)).strip()


def _walk_parts(payload: dict):
    yield payload
    for part in payload.get("parts", []) or []:
        yield from _walk_parts(part)


def _gmail_body_text(payload: dict) -> str:
    plain, html_body = "", ""
    for part in _walk_parts(payload):
        data = (part.get("body") or {}).get("data")
        if not data:
            continue
        mime = part.get("mimeType", "")
        if mime == "text/plain" and not plain:
            plain = _b64url_decode(data)
        elif mime == "text/html" and not html_body:
            html_body = _b64url_decode(data)
    return plain or _strip_html(html_body)


def _query_tokens(query: str) -> list[str]:
    """Turn Gmail search syntax into plain lowercase words for local matching."""
    cleaned = re.sub(r"\b(subject|from|to|newer_than|older_than|in|is|has|label)\s*:", " ", query, flags=re.I)
    return [t for t in re.findall(r"[\w'-]+", cleaned.lower()) if len(t) > 1]


# --------------------------------------------------------------------------- local fallback

def _search_local(query: str, max_results: int = 5) -> list[dict]:
    """Search ``personal_data/*.eml|*.txt``; results ranked by how many query words matched."""
    tokens = _query_tokens(query)
    hits = []
    if not PERSONAL_DATA_DIR.exists():
        return hits
    for path in sorted(PERSONAL_DATA_DIR.iterdir()):
        if path.suffix.lower() == ".eml":
            msg = email.message_from_bytes(path.read_bytes(), policy=email.policy.default)
            body_part = msg.get_body(preferencelist=("plain", "html"))
            body = body_part.get_content() if body_part else ""
            if body_part is not None and body_part.get_content_type() == "text/html":
                body = _strip_html(body)
            record = {
                "id": path.name,
                "from": msg.get("From", ""),
                "to": msg.get("To", ""),
                "subject": msg.get("Subject", ""),
                "date": msg.get("Date", ""),
                "body_text": body.strip(),
            }
        elif path.suffix.lower() == ".txt":
            body = path.read_text(encoding="utf-8", errors="replace")
            record = {"id": path.name, "from": "", "to": "", "subject": path.stem, "date": "", "body_text": body.strip()}
        else:
            continue
        haystack = f"{record['subject']}\n{record['body_text']}".lower()
        score = sum(1 for t in tokens if t in haystack)
        if tokens and score == 0:
            continue
        record["snippet"] = record["body_text"][:160]
        record["source"] = "local_file"
        record["_score"] = score
        hits.append(record)
    hits.sort(key=lambda r: -r["_score"])
    for r in hits:
        r.pop("_score", None)
    return hits[:max_results]


def _send_local(to: str, subject: str, body: str) -> dict:
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-request.md"
    path.write_text(f"# {subject}\n\n**To:** {to}\n\n{body}\n", encoding="utf-8")
    return {"id": str(path), "to": to, "subject": subject, "source": "local_file"}


# --------------------------------------------------------------------------- gmail

def search_inbox(query: str, max_results: int = 5) -> list[dict]:
    """Search mail with Gmail query syntax (e.g. ``subject:"Mission St" newer_than:30d``)."""
    if not google_ready():
        return _search_local(query, max_results)
    last_exc = None
    for attempt in range(2):  # a stale/expired cached client is rebuilt from the token file once
        try:
            gmail, _ = get_services()
            listing = gmail.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
            results = []
            for ref in listing.get("messages", []) or []:
                msg = gmail.users().messages().get(userId="me", id=ref["id"], format="full").execute()
                headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                results.append(
                    {
                        "id": msg["id"],
                        "from": headers.get("from", ""),
                        "to": headers.get("to", ""),
                        "subject": headers.get("subject", ""),
                        "date": headers.get("date", ""),
                        "snippet": msg.get("snippet", ""),
                        "body_text": _gmail_body_text(msg.get("payload", {})).strip(),
                        "source": "gmail",
                    }
                )
            return results
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            _reset_services()
    hits = _search_local(query, max_results)  # Gmail-side failure twice: fall back, but label it
    for hit in hits:
        hit["source"] = f"local_file (gmail unavailable: {type(last_exc).__name__}: {str(last_exc)[:80]})"
    return hits


def send_email(to: str, subject: str, body: str) -> dict:
    """Send a plain-text email from the authorised account (or write it to ``out/`` in fallback)."""
    if not google_ready():
        return _send_local(to, subject, body)
    last_exc = None
    for attempt in range(2):
        try:
            gmail, _ = get_services()
            mime = MIMEText(body, "plain", "utf-8")
            mime["to"] = to
            mime["subject"] = subject
            raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("ascii")
            sent = gmail.users().messages().send(userId="me", body={"raw": raw}).execute()
            return {"id": sent.get("id"), "threadId": sent.get("threadId"), "to": to, "subject": subject, "source": "gmail"}
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            _reset_services()
    result = _send_local(to, subject, body)  # never lose the request: write it locally, say why
    result["source"] = f"local_file (gmail failed: {type(last_exc).__name__}: {str(last_exc)[:120]})"
    return result


# --------------------------------------------------------------------------- calendar

_calendar = None
CALENDAR_TZ = os.environ.get("CALENDAR_TZ", "America/Los_Angeles")


def get_calendar():
    """Return the Calendar v3 service (same OAuth token as Gmail/Drive)."""
    global _calendar
    if _calendar is None:
        from googleapiclient.discovery import build

        _calendar = build("calendar", "v3", credentials=_load_credentials(), cache_discovery=False)
    return _calendar


def _reminder_local(summary: str, start_iso: str, notes: str) -> dict:
    OUT_DIR.mkdir(exist_ok=True)
    path = OUT_DIR / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-reminder.md"
    path.write_text(f"# Reminder: {summary}\n\n**When:** {start_iso}\n\n{notes}\n", encoding="utf-8")
    return {"id": str(path), "htmlLink": "", "summary": summary, "start": start_iso, "source": "local_file"}


def create_event(summary: str, start_iso: str, notes: str = "", minutes: int = 30) -> dict:
    """Create a calendar event. ``start_iso`` is a local time (2026-09-23T09:00) or a date
    (2026-09-23) for an all-day reminder. Falls back to a file in ``out/`` and says why."""
    if not google_ready():
        return _reminder_local(summary, start_iso, notes)
    try:
        if len(start_iso.strip()) == 10:
            day = datetime.strptime(start_iso.strip(), "%Y-%m-%d").date()
            when = {"start": {"date": day.isoformat()}, "end": {"date": (day + timedelta(days=1)).isoformat()}}
        else:
            start = datetime.fromisoformat(start_iso.strip())
            end = start + timedelta(minutes=minutes)
            when = {"start": {"dateTime": start.isoformat(), "timeZone": CALENDAR_TZ},
                    "end": {"dateTime": end.isoformat(), "timeZone": CALENDAR_TZ}}
        body = {"summary": summary, "description": notes, **when,
                "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 30}]}}
        created = get_calendar().events().insert(calendarId="primary", body=body).execute()
        return {"id": created.get("id"), "htmlLink": created.get("htmlLink"), "summary": summary,
                "start": start_iso, "source": "google"}
    except Exception as exc:  # noqa: BLE001 - never lose the reminder: write it locally, say why
        _reset_services()
        result = _reminder_local(summary, start_iso, notes)
        result["source"] = f"local_file (calendar failed: {type(exc).__name__}: {str(exc)[:120]})"
        return result


# --------------------------------------------------------------------------- drive

def list_drive_files(name_contains: str, max_results: int = 10) -> list[dict]:
    """List Drive files whose name contains the text (empty string = most recent files)."""
    if not google_ready():
        files = [p for p in (PERSONAL_DATA_DIR.iterdir() if PERSONAL_DATA_DIR.exists() else []) if p.is_file()]
        files = [p for p in files if name_contains.lower() in p.name.lower()]
        return [
            {"id": str(p), "name": p.name, "mimeType": "text/plain", "modifiedTime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(), "webViewLink": "", "source": "local_file"}
            for p in files[:max_results]
        ]
    _, drive = get_services()
    q = "trashed = false"
    if name_contains:
        q += " and name contains '" + name_contains.replace("'", "\\'") + "'"
    resp = drive.files().list(q=q, pageSize=max_results, orderBy="modifiedTime desc", fields="files(id,name,mimeType,modifiedTime,webViewLink)").execute()
    return [{**f, "source": "drive"} for f in resp.get("files", [])]


def read_drive_file(file_id: str) -> str:
    """Return the text of a Google Doc, text/markdown file or PDF stored in Drive."""
    if not google_ready():
        return Path(file_id).read_text(encoding="utf-8", errors="replace")
    from googleapiclient.http import MediaIoBaseDownload

    _, drive = get_services()
    meta = drive.files().get(fileId=file_id, fields="id,name,mimeType").execute()
    mime = meta.get("mimeType", "")
    if mime == GOOGLE_DOC:
        request = drive.files().export_media(fileId=file_id, mimeType="text/plain")
    elif mime in _TEXT_MIMES or mime == "application/pdf":
        request = drive.files().get_media(fileId=file_id)
    else:
        raise ValueError(f"Unsupported Drive file type {mime!r} for {meta.get('name')!r}")
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    data = buf.getvalue()
    if mime == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    return data.decode("utf-8", errors="replace")
