#!/usr/bin/env python3
"""Deploy check: confirms the SMTP password on the server can log in (sends nothing)."""
import smtplib
import ssl

env = dict(line.strip().split("=", 1) for line in open("/etc/ali-booking.env") if "=" in line)
if not env.get("SMTP_PASS"):
    raise SystemExit("SMTP check: SMTP_PASS is empty on the server")
with smtplib.SMTP_SSL(env["SMTP_HOST"], int(env["SMTP_PORT"]), context=ssl.create_default_context(), timeout=20) as s:
    s.login(env["SMTP_USER"], env["SMTP_PASS"])
print("SMTP check: login OK for", env["SMTP_USER"])
