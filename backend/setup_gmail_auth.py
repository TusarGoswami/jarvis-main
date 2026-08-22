import sys
import os
import json

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google_auth_oauthlib.flow import InstalledAppFlow
from app.core.email_tool import save_gmail_credentials, GMAIL_SCOPES, GMAIL_TOKEN_PATH

def run_gmail_oauth_setup(credentials_path: str):
    """
    Executes a one-time installed application OAuth flow to obtain a refresh token
    with strict 'gmail.send' scope, encrypting the token at rest in ~/.jarvis/gmail_token.json.
    """
    if not os.path.exists(credentials_path):
        print(f"[ERROR] Client secrets file not found: {credentials_path}")
        print("Please download your OAuth client credentials JSON from Google Cloud Console.")
        return False

    print("=" * 65)
    print("VOCALIS AI — GMAIL OAUTH SETUP")
    print("=" * 65)
    print(f"Loading client secrets from: {credentials_path}")
    print(f"Requesting scope: {GMAIL_SCOPES[0]} (Send Only)")
    print("A browser window will open for you to grant permission...\n")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_path,
            scopes=GMAIL_SCOPES
        )
        creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

        if not creds or not creds.refresh_token:
            print("\n[WARNING] No refresh token returned. If you have previously authorized this app,")
            print("please revoke access in your Google Account security settings or re-run with consent prompt.")
            # If client_id/secret are available, we can still save if refresh_token was retrieved
            if not creds.refresh_token:
                return False

        # Save encrypted token
        token_file = save_gmail_credentials(
            refresh_token=creds.refresh_token,
            client_id=creds.client_id or "",
            client_secret=creds.client_secret or ""
        )

        print("\n[SUCCESS] Gmail OAuth setup complete!")
        print(f"Encrypted token saved to: {token_file}")
        print("Vocalis AI is now ready to send emails securely via Gmail API.")
        return True

    except Exception as e:
        print(f"\n[ERROR] OAuth authentication failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        creds_file = sys.argv[1]
    else:
        # Default lookups in current or backend directory
        default_files = ["credentials.json", "client_secret.json", os.path.join(os.path.dirname(__file__), "credentials.json")]
        creds_file = next((f for f in default_files if os.path.exists(f)), None)

    if creds_file and os.path.exists(creds_file):
        run_gmail_oauth_setup(creds_file)
    else:
        print("VOCALIS AI — GMAIL OAUTH SETUP")
        print("-" * 40)
        print("Usage:")
        print("  python setup_gmail_auth.py <path_to_client_secret_json>")
        print("\nSteps:")
        print("  1. Go to Google Cloud Console (https://console.cloud.google.com).")
        print("  2. Create an OAuth 2.0 Client ID for a 'Desktop Application'.")
        print("  3. Download the credentials JSON file (e.g. credentials.json).")
        print("  4. Run: python setup_gmail_auth.py credentials.json")
