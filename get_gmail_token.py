from google_auth_oauthlib.flow import InstalledAppFlow
import json

# Scopes needed for Gmail
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_token():
    """Get Gmail OAuth2 Bearer Token"""
    
    # This will open your browser
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json',
        SCOPES
    )
    
    # This handles the OAuth2 flow locally
    creds = flow.run_local_server(port=8080)
    
    # Print the access token
    token = creds.token
    
    print("\n" + "="*70)
    print("✅ SUCCESS! Here's your GMAIL_BEARER_TOKEN:")
    print("="*70)
    print(f"\n{token}\n")
    print("="*70)
    print("\nCopy the token above and paste into .env:")
    print("GMAIL_BEARER_TOKEN=<paste_token_here>\n")
    
    # Optional: Save refresh token for later
    if creds.refresh_token:
        print(f"Refresh token (for future use): {creds.refresh_token}\n")

if __name__ == '__main__':
    get_gmail_token()