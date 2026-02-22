"""Flood Alert Email Tool.

A LangChain tool that sends a single, cleanly formatted flood alert email.
Used by the Flood Orchestrator agent when a location is rated
CRITICAL or HIGH severity.
"""

import os
import re
from datetime import datetime

from langchain_core.tools import tool

from app.tools.email_tool import send_email


def _clean_body(body: str) -> str:
    """Remove markdown formatting and deduplicate repeated content.
    
    The LLM sometimes outputs markdown (**bold**, *italic*) and may
    repeat blocks. This cleans the body for plain-text email.
    """
    # Strip markdown bold/italic markers
    body = re.sub(r'\*\*(.+?)\*\*', r'\1', body)
    body = re.sub(r'\*(.+?)\*', r'\1', body)

    # Deduplicate: if the body contains "Dear" more than once,
    # keep only the first complete letter
    dear_splits = body.split("Dear ")
    if len(dear_splits) > 2:
        # Keep intro + first "Dear..." letter
        body = dear_splits[0] + "Dear " + dear_splits[1]

    # Remove excessive special characters that email clients mangle
    body = body.replace("═", "=")
    body = body.replace("─", "-")
    body = body.replace("🚨", "[ALERT]")
    body = body.replace("🔴", "[CRITICAL]")
    body = body.replace("🟠", "[HIGH]")
    body = body.replace("🟡", "[MODERATE]")

    # Collapse multiple blank lines
    body = re.sub(r'\n{3,}', '\n\n', body)

    return body.strip()


@tool
def send_flood_alert_email(
    subject: str,
    body: str,
) -> str:
    """Send a detailed flood alert email to the configured recipient.

    IMPORTANT: Call this tool EXACTLY ONCE with the complete alert.
    Do NOT call it multiple times.

    Use this tool ONLY when one or more locations are rated CRITICAL or HIGH
    severity for flood risk. The email should contain:
    - All CRITICAL and HIGH severity locations
    - Their coordinates (latitude, longitude)
    - Evidence from sensor data and/or web intelligence
    - Recommended actions (evacuation, relief deployment, etc.)

    Args:
        subject: Email subject line. Keep it short, e.g. 'FLOOD ALERT: 3 Critical Locations in Chennai'
        body: Detailed email body with all flood risk information. Plain text, no markdown.

    Returns:
        Success or failure message.
    """
    recipient = os.environ.get("USER_EMAIL", "")

    print(f"     📧  [EMAIL] Preparing flood alert email …")
    print(f"     📧  [EMAIL] Recipient: {recipient or '(NOT SET)'}")
    print(f"     📧  [EMAIL] Subject: {subject[:80]}")

    if not recipient or "@" not in recipient:
        print("     ❌  [EMAIL] USER_EMAIL not configured — cannot send!")
        return (
            "ERROR: USER_EMAIL not configured in environment. "
            "Please set USER_EMAIL in the .env file to receive flood alerts."
        )

    # Clean up the subject
    subject = subject.replace("🚨", "").strip()
    if "FLOOD" not in subject.upper():
        subject = f"FLOOD ALERT: {subject}"

    # Clean the body
    body = _clean_body(body)

    # Build a clean, professional plain-text email
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    full_body = (
        f"{'=' * 55}\n"
        f"  HeliosCommand - AUTOMATED FLOOD ALERT\n"
        f"  Generated: {now}\n"
        f"{'=' * 55}\n\n"
        f"{body}\n\n"
        f"{'-' * 55}\n"
        f"This alert was generated automatically by HeliosCommand\n"
        f"based on sensor data analysis and web intelligence.\n"
        f"Please take appropriate action immediately.\n"
        f"{'-' * 55}\n"
    )

    print(f"     📧  [EMAIL] Body: {len(full_body)} chars (cleaned)")
    print(f"     📧  [EMAIL] Sending via Gmail API …")

    result = send_email(recipient, subject, full_body)

    if result.get("success"):
        print(f"     ✅  [EMAIL] Sent successfully to {recipient}")
        return f"Email sent successfully to {recipient}. Do NOT call this tool again."
    else:
        error = result.get("error", "Unknown error")
        print(f"     ❌  [EMAIL] Failed: {error}")
        return f"Failed to send email: {error}. Do NOT retry."


def get_flood_email_tools():
    """Return the flood alert email tool list."""
    return [send_flood_alert_email]
