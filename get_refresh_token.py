"""
OAuth2 Refresh Token Generator Helper for Google Business Profile.

Guides you through generating a permanent refresh_token and saves it to .env.
"""

import sys
import urllib.parse
import requests
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

from config import CLIENT_ID, CLIENT_SECRET

TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
SCOPE = "https://www.googleapis.com/auth/business.manage"
DEFAULT_REDIRECT_URI = "https://developers.google.com/oauthplayground"


def exchange_code_for_refresh_token(code: str, redirect_uri: str) -> str:
    """Exchange an authorization code for refresh token."""
    payload = {
        "code": code.strip(),
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": redirect_uri.strip(),
        "grant_type": "authorization_code",
    }
    response = requests.post(TOKEN_URL, data=payload, timeout=20)
    data = response.json()

    if response.status_code == 200 and "refresh_token" in data:
        refresh_token = data["refresh_token"]
        return refresh_token
    else:
        err = data.get("error_description") or data.get("error") or response.text
        raise RuntimeError(f"Token exchange failed ({response.status_code}): {err}")


def save_refresh_token_to_env(refresh_token: str):
    """Update .env file with the new refresh token."""
    if not ENV_FILE.exists():
        return

    content = ENV_FILE.read_text(encoding="utf-8")
    lines = content.splitlines()
    new_lines = []
    found = False

    for line in lines:
        if line.startswith("REFRESH_TOKEN="):
            new_lines.append(f"REFRESH_TOKEN={refresh_token}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"REFRESH_TOKEN={refresh_token}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"✅ Successfully saved REFRESH_TOKEN to .env!")


def main():
    print("\n" + "=" * 70)
    print("🔑 GOOGLE BUSINESS PROFILE OAUTH2 REFRESH TOKEN GENERATOR")
    print("=" * 70)

    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ Error: CLIENT_ID and CLIENT_SECRET must be set in .env first.")
        return

    print(f"• Client ID:     {CLIENT_ID[:15]}...{CLIENT_ID[-15:]}")
    print(f"• Scope Needed:  {SCOPE}")
    print("-" * 70)

    # Option 1: Direct URL generation
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": DEFAULT_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent"
    }
    auth_link = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    print("\n👉 OPTION 1 (Google OAuth 2.0 Playground - Easiest 2-minute method):")
    print("1. In Google Cloud Console, ensure Authorized Redirect URI includes:")
    print(f"   https://developers.google.com/oauthplayground")
    print("2. Open https://developers.google.com/oauthplayground in your browser.")
    print("3. Click the gear icon (top right):")
    print("   - Check 'Use your own OAuth credentials'")
    print(f"   - Enter Client ID:     {CLIENT_ID}")
    print(f"   - Enter Client Secret: {CLIENT_SECRET}")
    print("4. In Step 1 (left side), paste scope:")
    print(f"   https://www.googleapis.com/auth/business.manage")
    print("   and click 'Authorize APIs'.")
    print("5. Sign in with your Google account that manages ParentingHub GBP.")
    print("6. In Step 2, click 'Exchange authorization code for tokens'.")
    print("7. Copy the 'Refresh token' value and paste it into .env or below.")

    print("\n" + "-" * 70)
    user_input = input("\nEnter your REFRESH_TOKEN (or authorization code if ready, or press Enter to exit): ").strip()

    if user_input:
        if user_input.startswith("1//") or len(user_input) > 40:
            save_refresh_token_to_env(user_input)
        else:
            try:
                print("[*] Exchanging authorization code...")
                tok = exchange_code_for_refresh_token(user_input, DEFAULT_REDIRECT_URI)
                save_refresh_token_to_env(tok)
            except Exception as e:
                print(f"❌ {e}")
                print("Tip: If code exchange failed, paste the raw refresh_token directly.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
