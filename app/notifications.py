"""
notifications.py — Async SMS (Twilio) + Email (Gmail SMTP) notifications.
Both run in background tasks so they never block the scanner loop.
"""
import os, smtplib, logging
from email.mime.text import MIMEText
from datetime import datetime

log = logging.getLogger(__name__)

TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM  = os.getenv("TWILIO_FROM_NUMBER", "")
GMAIL_USER   = os.getenv("GMAIL_USER", "")
GMAIL_PASS   = os.getenv("GMAIL_APP_PASSWORD", "")
FROM_NAME    = os.getenv("NOTIFICATION_FROM_NAME", "School Attendance System")


def _format_message(name: str, scan_type: str, scanned_at: str) -> str:
    try:
        dt = datetime.fromisoformat(scanned_at)
        time_str = dt.strftime("%I:%M %p")
        date_str = dt.strftime("%B %d, %Y")
    except Exception:
        time_str = date_str = scanned_at
    return (
        f"Notice: {name} has successfully registered {scan_type} "
        f"at {time_str} on {date_str}."
    )


def send_sms(to_number: str, message: str):
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM]):
        log.warning("Twilio not configured — skipping SMS.")
        return
    try:
        from twilio.rest import Client
        Client(TWILIO_SID, TWILIO_TOKEN).messages.create(
            body=message, from_=TWILIO_FROM, to=to_number
        )
        log.info("SMS sent to %s", to_number)
    except Exception as exc:
        log.error("SMS failed: %s", exc)


def send_email(to_email: str, subject: str, message: str):
    if not all([GMAIL_USER, GMAIL_PASS]):
        log.warning("Gmail not configured — skipping email.")
        return
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"]    = f"{FROM_NAME} <{GMAIL_USER}>"
        msg["To"]      = to_email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.send_message(msg)
        log.info("Email sent to %s", to_email)
    except Exception as exc:
        log.error("Email failed: %s", exc)


def notify(user: dict, scan_type: str, scanned_at: str):
    """Fire-and-forget: call from BackgroundTasks."""
    msg = _format_message(user["full_name"], scan_type, scanned_at)
    subject = f"Attendance Alert — {user['full_name']} {scan_type}"
    if user.get("parent_phone"):
        send_sms(user["parent_phone"], msg)
    if user.get("parent_email"):
        send_email(user["parent_email"], subject, msg)
