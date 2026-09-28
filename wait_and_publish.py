"""
Live listener that waits for Google My Business API to propagate and publishes automatically.
"""

import time
import requests
from publisher import refresh_access_token, build_post_payload
from generator import generate_post_content, record_successful_post

def wait_and_publish():
    print("=" * 65)
    print("⏳ Listening for Google My Business API activation...")
    print("=" * 65)

    success, access_token, err = refresh_access_token()
    if not success:
        print(f"❌ OAuth Error: {err}")
        return

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    url = "https://mybusiness.googleapis.com/v4/accounts/3273073795777079272/locations/17062544117938448005/localPosts"

    attempts = 0
    while attempts < 30:
        attempts += 1
        print(f"[*] Check {attempts}/30: Probing Google API gateway...")

        post_data = generate_post_content()
        payload = build_post_payload(post_data["content"])

        r = requests.post(url, headers=headers, json=payload, timeout=15)

        if r.status_code in (200, 201):
            print("\n" + "🎉" * 20)
            print("🚀 SUCCESS! POST HAS BEEN PUBLISHED TO GOOGLE BUSINESS PROFILE!")
            print("Response:", r.text)
            print("🎉" * 20 + "\n")
            record_successful_post(post_data, gbp_response=r.json())
            return
        elif r.status_code == 403 and "disabled" in r.text.lower():
            print("   ⚠️  Status: API still propagating on Google's servers. Retrying in 10s...")
            time.sleep(10)
        else:
            print(f"   ℹ️  API Response ({r.status_code}): {r.text[:200]}")
            time.sleep(10)

    print("Timed out waiting. Please ensure the API is enabled in Google Cloud Console.")

if __name__ == "__main__":
    wait_and_publish()
