"""Gmail send helper (app-level).

Uses `GMAIL_BEARER_TOKEN` from environment and posts to Gmail REST API.
"""
import base64
import os
from email.message import EmailMessage
from typing import Dict

import requests


def send_email(to_address: str, subject: str, body: str) -> Dict[str, str]:
    token = os.environ.get("GMAIL_BEARER_TOKEN")
    user = os.environ.get("GMAIL_USER_ID", "me")
    if not token:
        return {"success": False, "error": "GMAIL_BEARER_TOKEN not set in environment"}

    msg = EmailMessage()
    msg["To"] = to_address
    msg["From"] = user if user != "me" else "me"
    msg["Subject"] = subject
    msg.set_content(body)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")

    url = f"https://gmail.googleapis.com/gmail/v1/users/{user}/messages/send"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"raw": raw}

    resp = requests.post(url, headers=headers, json=payload, timeout=10)
    try:
        resp.raise_for_status()
    except Exception:
        return {"success": False, "error": f"Gmail API error: {resp.text}"}

    return {"success": True, "result": resp.json()}
from tools.email_tool import send_email

__all__ = ["send_email"]
