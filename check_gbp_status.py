"""
Diagnostic script to check Google Business Profile API enablement and token permissions.
"""

import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()
from publisher import refresh_access_token

def check_all():
    print("=" * 65)
    print("🔍 GOOGLE BUSINESS PROFILE API DIAGNOSTIC")
    print("=" * 65)

    success, access_token, err = refresh_access_token()
    if not success:
        print(f"❌ OAuth Refresh Token Error: {err}")
        return

    print("✅ OAuth2 Access Token successfully refreshed!")
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    apis = [
        ("Google My Business API (v4 LocalPosts)", "https://mybusiness.googleapis.com/v4/accounts/123/locations/17062544117938448005/localPosts", "https://console.developers.google.com/apis/api/mybusiness.googleapis.com/overview?project=518149919537"),
        ("My Business Business Information API", "https://mybusinessbusinessinformation.googleapis.com/v1/locations/17062544117938448005?readMask=name,title", "https://console.developers.google.com/apis/api/mybusinessbusinessinformation.googleapis.com/overview?project=518149919537"),
        ("My Business Account Management API", "https://mybusinessaccountmanagement.googleapis.com/v1/accounts", "https://console.developers.google.com/apis/api/mybusinessaccountmanagement.googleapis.com/overview?project=518149919537"),
        ("Business Profile Performance API", "https://businessprofileperformance.googleapis.com/v1/locations/17062544117938448005:fetchMultiDailyMetricsTimeSeries", "https://console.developers.google.com/apis/api/businessprofileperformance.googleapis.com/overview?project=518149919537")
    ]

    for name, url, enable_link in apis:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            print(f"✅ {name}: ENABLED & WORKING (200 OK)")
            print(f"   Response: {r.text[:100]}")
        elif r.status_code == 403:
            print(f"⚠️  {name}: DISABLED (403 Forbidden)")
            print(f"   👉 Enable here: {enable_link}")
        elif r.status_code == 429:
            print(f"⚠️  {name}: Quota/Rate Limit (429)")
        else:
            print(f"ℹ️  {name}: Status {r.status_code}")

    print("=" * 65)

if __name__ == "__main__":
    check_all()
