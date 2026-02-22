import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip('"\'')
auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip('"\'')

client = Client(account_sid, auth_token)

# Get last 5 messages
messages = client.messages.list(limit=5)

for record in messages:
    print(f"SID: {record.sid}")
    print(f"Date: {record.date_created}")
    print(f"To: {record.to}")
    print(f"Status: {record.status}")
    print(f"Body: {record.body[:50]}...")
    print(f"Error Code: {record.error_code}")
    print(f"Error Message: {record.error_message}")
    print("-" * 40)
