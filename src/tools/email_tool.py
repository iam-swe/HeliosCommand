"""Compatibility wrapper re-exporting app-level Gmail helper."""
from app.tools.email_tool import send_email

__all__ = ["send_email"]
