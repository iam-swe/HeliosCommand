"""Flood Alert SMS Tool.

A LangChain tool that sends a short flood alert SMS via Twilio.
Used by the Flood Orchestrator agent alongside the email tool when a location
is rated CRITICAL or HIGH severity.
"""

import os
from twilio.rest import Client
from langchain_core.tools import tool


@tool
def send_flood_alert_sms(
    body: str,
) -> str:
    """Send a short SMS flood alert to the configured recipient.

    IMPORTANT: Call this tool EXACTLY ONCE with the alert summary.
    Do NOT call it multiple times.

    Use this tool ONLY when one or more locations are rated CRITICAL or HIGH
    severity for flood risk. The SMS should be concise (under 320 characters)
    and contain:
    - The number of CRITICAL and HIGH severity locations
    - A brief summary of the most severe risk.
    - An instruction to check their email for full details.

    Args:
        body: Short SMS body with the flood alert summary (max 320 chars).

    Returns:
        Success or failure message.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip('"\'')
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip('"\'')
    from_phone_number = os.getenv("TWILIO_PHONE_NUMBER", "").strip('"\'')
    to_phone_number = os.getenv("RECIPIENT_PHONE_NUMBER", "").strip('"\'')

    print(f"     📱  [SMS] Preparing flood alert SMS …")
    print(f"     📱  [SMS] Recipient: {to_phone_number or '(NOT SET)'}")

    if not all([account_sid, auth_token, from_phone_number, to_phone_number]):
        missing = [
            k for k, v in {
                "TWILIO_ACCOUNT_SID": account_sid,
                "TWILIO_AUTH_TOKEN": auth_token,
                "TWILIO_PHONE_NUMBER": from_phone_number,
                "RECIPIENT_PHONE_NUMBER": to_phone_number
            }.items() if not v
        ]
        print(f"     ❌  [SMS] Missing Twilio config: {', '.join(missing)} — cannot send!")
        return (
            f"ERROR: Missing Twilio configuration ({', '.join(missing)}). "
            "Please set these in the .env file to receive SMS alerts."
        )

    # Clean the body
    import re
    body = body.strip()
    body = re.sub(r'\*\*(.+?)\*\*', r'\1', body)
    body = re.sub(r'\*(.+?)\*', r'\1', body)
    
    # Strip emojis that might trigger spam filters
    body = body.replace("🚨", "").replace("🔴", "").replace("🟠", "").replace("🟡", "")

    if not body.upper().startswith("FLOOD ALERT"):
        body = f"FLOOD ALERT:\n{body}"

    # Enforce concise length
    if len(body) > 320:
        body = body[:317] + "..."

    print(f"     📱  [SMS] Body: {len(body)} chars")
    print(f"     📱  [SMS] Sending via Twilio API …")

    try:
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            body=body,
            from_=from_phone_number,
            to=to_phone_number
        )

        print(f"     ✅  [SMS] Sent successfully! SID: {message.sid}")
        return f"SMS sent successfully. SID: {message.sid}. Do NOT call this tool again."
    except Exception as e:
        error_msg = str(e)
        print(f"     ❌  [SMS] Failed: {error_msg}")
        return f"Failed to send SMS: {error_msg}. Do NOT retry."


def get_flood_sms_tools():
    """Return the flood alert SMS tool list."""
    return [send_flood_alert_sms]
