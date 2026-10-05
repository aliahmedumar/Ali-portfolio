#!/usr/bin/env python3
"""Booking endpoint for ali.cloudordinate.com.

POST /api/book  -> emails the request (with a calendar invite) to MAIL_TO via SMTP.
GET  /api/health

Config comes from environment (systemd EnvironmentFile):
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, MAIL_TO, PORT
"""
import json
import os
import re
import smtplib
import ssl
import time
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formataddr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.hostinger.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
MAIL_TO = os.environ.get("MAIL_TO", SMTP_USER)
PORT = int(os.environ.get("PORT", "8089"))

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LIMITS = {"name": 100, "email": 200, "company": 150, "message": 3000, "slot_label": 200}
MAX_BODY = 16 * 1024
RATE_MAX, RATE_WINDOW = 5, 3600
CALL_MINUTES = 30

_hits = {}
_lock = Lock()


def rate_limited(ip):
    now = time.time()
    with _lock:
        hits = [t for t in _hits.get(ip, []) if now - t < RATE_WINDOW]
        if len(hits) >= RATE_MAX:
            _hits[ip] = hits
            return True
        hits.append(now)
        _hits[ip] = hits
        return False


def one_line(value):
    return re.sub(r"[\r\n\t]+", " ", value).strip()


def ics_escape(value):
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def build_invite(start, name, email, summary):
    fmt = "%Y%m%dT%H%M%SZ"
    end = start + timedelta(minutes=CALL_MINUTES)
    return "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ali.cloudordinate.com//booking//EN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uuid.uuid4()}@ali.cloudordinate.com",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime(fmt)}",
        f"DTSTART:{start.strftime(fmt)}",
        f"DTEND:{end.strftime(fmt)}",
        f"SUMMARY:{ics_escape('Call with ' + name)}",
        f"DESCRIPTION:{ics_escape(summary)}",
        f"ORGANIZER:mailto:{MAIL_TO}",
        f"ATTENDEE;CN={ics_escape(name)}:mailto:{email}",
        "END:VEVENT",
        "END:VCALENDAR",
        "",
    ])


def validate(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid request.")
    clean = {}
    for key, limit in LIMITS.items():
        value = data.get(key, "")
        if not isinstance(value, str):
            raise ValueError("Invalid request.")
        value = value.strip()
        if len(value) > limit:
            raise ValueError(f"{key.capitalize()} is too long.")
        clean[key] = value
    if not clean["name"]:
        raise ValueError("Please add your name.")
    if not EMAIL_RE.match(clean["email"]):
        raise ValueError("Please add a valid email.")
    if not clean["message"]:
        raise ValueError("Tell me a little about the project.")
    try:
        start = datetime.fromisoformat(str(data.get("slot", "")).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Please pick a time.")
    if start.tzinfo is None:
        raise ValueError("Please pick a time.")
    start = start.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if start < now or start > now + timedelta(days=62):
        raise ValueError("That time is not available.")
    clean["name"] = one_line(clean["name"])
    clean["email"] = one_line(clean["email"])
    clean["company"] = one_line(clean["company"])
    clean["slot_label"] = one_line(clean["slot_label"]) or start.strftime("%a %d %b %Y %H:%M UTC")
    clean["start"] = start
    return clean


def send(req):
    summary = (
        f"Name: {req['name']}\n"
        f"Email: {req['email']}\n"
        f"Company: {req['company'] or '(not given)'}\n"
        f"Requested time: {req['slot_label']} ({req['start'].strftime('%Y-%m-%d %H:%M UTC')})\n\n"
        f"{req['message']}\n"
    )
    msg = EmailMessage()
    msg["Subject"] = f"Call request: {req['name']}, {req['slot_label']}"
    msg["From"] = formataddr(("Portfolio booking", SMTP_USER))
    msg["To"] = MAIL_TO
    msg["Reply-To"] = formataddr((req["name"], req["email"]))
    msg.set_content(summary)
    msg.add_attachment(
        build_invite(req["start"], req["name"], req["email"], summary).encode(),
        maintype="text", subtype="calendar", filename="invite.ics",
    )
    ctx = ssl.create_default_context()
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=20) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.starttls(context=ctx)
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)


class Handler(BaseHTTPRequestHandler):
    server_version = "booking"

    def reply(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def client_ip(self):
        fwd = self.headers.get("X-Forwarded-For", "")
        return fwd.split(",")[0].strip() or self.client_address[0]

    def do_GET(self):
        if self.path == "/api/health":
            return self.reply(200, {"ok": True})
        self.reply(404, {"error": "Not found."})

    def do_POST(self):
        if self.path != "/api/book":
            return self.reply(404, {"error": "Not found."})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return self.reply(413, {"error": "Request too large."})
        try:
            data = json.loads(self.rfile.read(length))
        except ValueError:
            return self.reply(400, {"error": "Invalid request."})
        if isinstance(data, dict) and data.get("website"):
            return self.reply(200, {"ok": True})  # honeypot filled: silently drop
        if rate_limited(self.client_ip()):
            return self.reply(429, {"error": "Too many requests. Please email me instead."})
        try:
            req = validate(data)
        except ValueError as e:
            return self.reply(400, {"error": str(e)})
        try:
            send(req)
        except Exception as e:  # noqa: BLE001
            self.log_error("send failed: %r", e)
            return self.reply(502, {"error": "Could not send right now. Please email ali@cloudordinate.com."})
        self.reply(200, {"ok": True})

    def log_message(self, fmt, *args):
        print("%s %s" % (self.client_ip(), fmt % args), flush=True)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
