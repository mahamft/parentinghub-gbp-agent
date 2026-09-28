"""
Google Business Profile (GBP) Publisher module.

Handles OAuth2 refresh token exchange and publishes standard update posts
to Google Business Profile via the Google My Business v4 LocalPosts API.
"""

import logging
from typing import Dict, Any, Optional, Tuple
import requests

from config import (
    CLIENT_ID,
    CLIENT_SECRET,
    REFRESH_TOKEN,
    ACCOUNT_ID,
    LOCATION_ID,
    CTA_ACTION,
    CTA_URL,
    GBP_WEBHOOK_URL,
    validate_gbp_config,
)

logger = logging.getLogger("parentinghub.publisher")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
MYBUSINESS_API_BASE = "https://mybusiness.googleapis.com/v4"
MYBUSINESS_ACCOUNTS_V1 = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"


def refresh_access_token(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    refresh_token: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Exchange OAuth2 refresh token for a short-lived access token.
    Returns (success, access_token, error_message).
    """
    c_id = client_id or CLIENT_ID
    c_sec = client_secret or CLIENT_SECRET
    r_tok = refresh_token or REFRESH_TOKEN

    if not (c_id and c_sec and r_tok):
        return False, None, "Missing OAuth2 credentials (CLIENT_ID, CLIENT_SECRET, or REFRESH_TOKEN)."

    payload = {
        "client_id": c_id,
        "client_secret": c_sec,
        "refresh_token": r_tok,
        "grant_type": "refresh_token",
    }

    try:
        response = requests.post(GOOGLE_OAUTH_TOKEN_URL, data=payload, timeout=15)
        data = response.json()

        if response.status_code == 200 and "access_token" in data:
            logger.info("Successfully refreshed Google OAuth2 access token.")
            return True, data["access_token"], None
        else:
            error_msg = data.get("error_description") or data.get("error") or response.text
            logger.error(f"Failed to refresh access token: {error_msg} (Status: {response.status_code})")
            return False, None, f"OAuth Token Error ({response.status_code}): {error_msg}"

    except requests.RequestException as e:
        logger.error(f"Network error during OAuth token refresh: {e}")
        return False, None, f"Network error during token refresh: {str(e)}"


def discover_account_id(access_token: str) -> Optional[str]:
    """
    Auto-discover Google Business Profile Account ID for the authenticated user.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        r = requests.get(MYBUSINESS_ACCOUNTS_V1, headers=headers, timeout=10)
        if r.status_code == 200:
            accounts = r.json().get("accounts", [])
            if accounts:
                acc_name = accounts[0].get("name")  # e.g., 'accounts/123456789'
                logger.info(f"Discovered Google Business Profile account: {acc_name}")
                return acc_name
    except Exception as e:
        logger.debug(f"Account auto-discovery attempt: {e}")
    return None


def format_location_url(location_id: str, account_id: Optional[str] = None, access_token: Optional[str] = None) -> str:
    """
    Format the GBP LocalPosts API URL properly based on the provided LOCATION_ID and ACCOUNT_ID.
    """
    loc = location_id.strip().strip("/")
    acc = (ACCOUNT_ID if account_id is None else account_id).strip().strip("/")

    # If location already has full resource path 'accounts/{acc}/locations/{loc}'
    if loc.startswith("accounts/"):
        return f"{MYBUSINESS_API_BASE}/{loc}/localPosts"

    # If location is 'locations/{loc}' or '{loc}'
    raw_loc = loc if loc.startswith("locations/") else f"locations/{loc}"

    # If account_id is provided or discovered
    if not acc and access_token:
        discovered = discover_account_id(access_token)
        if discovered:
            acc = discovered.strip().strip("/")

    if acc:
        raw_acc = acc if acc.startswith("accounts/") else f"accounts/{acc}"
        return f"{MYBUSINESS_API_BASE}/{raw_acc}/{raw_loc}/localPosts"

    return f"{MYBUSINESS_API_BASE}/{raw_loc}/localPosts"


def build_post_payload(
    post_summary: str,
    cta_action: Optional[str] = None,
    cta_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build the JSON payload for a Google Business Profile STANDARD LocalPost.
    """
    action = cta_action or CTA_ACTION or "LEARN_MORE"
    target_url = cta_url or CTA_URL or "https://parentinghub.pk/"

    payload = {
        "languageCode": "en",
        "summary": post_summary,
        "topicType": "STANDARD",
        "callToAction": {
            "actionType": action,
            "url": target_url
        }
    }
    return payload


def publish_via_webhook(
    post_summary: str,
    link: Optional[str] = None,
    image_url: Optional[str] = None,
    webhook_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Publish post payload directly to Make.com / Buffer Webhook.
    """
    target_webhook = webhook_url or GBP_WEBHOOK_URL
    target_link = link or CTA_URL or "https://parentinghub.pk/"
    target_image_url = image_url or "https://www.parentinghub.pk/assets/feeder-b349f53c.png"

    if not target_webhook:
        return {
            "success": False,
            "post_id": None,
            "response": None,
            "error": "GBP_WEBHOOK_URL is not configured."
        }

    payload = {
        "summary": post_summary,
        "link": target_link,
        "image_url": target_image_url
    }

    try:
        logger.info(f"Dispatching post to Make.com webhook: {target_webhook[:35]}...")
        response = requests.post(target_webhook, json=payload, timeout=25)
        if response.status_code in (200, 201, 202, 204):
            logger.info("Successfully dispatched post to Make.com / Buffer webhook!")
            return {
                "success": True,
                "post_id": f"make_webhook_{response.status_code}",
                "response": {"status": response.status_code, "text": response.text},
                "error": None
            }
        else:
            err = f"Webhook returned status {response.status_code}: {response.text}"
            logger.error(err)
            return {
                "success": False,
                "post_id": None,
                "response": {"status": response.status_code, "text": response.text},
                "error": err
            }
    except Exception as e:
        err = f"Error publishing via webhook: {e}"
        logger.error(err)
        return {
            "success": False,
            "post_id": None,
            "response": None,
            "error": err
        }


def publish_to_gbp(
    post_text: str,
    location_id: Optional[str] = None,
    cta_action: Optional[str] = None,
    cta_url: Optional[str] = None,
    image_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Publish a post to Google Business Profile (via Webhook if configured, or direct OAuth API).

    Returns a status dictionary:
    {
        "success": bool,
        "post_id": Optional[str],
        "response": Optional[Dict],
        "error": Optional[str]
    }
    """
    if GBP_WEBHOOK_URL:
        logger.info("Using Make.com Webhook publisher pipeline.")
        return publish_via_webhook(post_text, link=cta_url or CTA_URL, image_url=image_url)

    loc_id = location_id or LOCATION_ID

    if not validate_gbp_config():
        error_msg = (
            "Google Business Profile credentials are not fully configured in .env. "
            "Please provide CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, and LOCATION_ID, or GBP_WEBHOOK_URL."
        )
        logger.error(error_msg)
        return {
            "success": False,
            "post_id": None,
            "response": None,
            "error": error_msg
        }

    # Step 1: Refresh Access Token
    success, access_token, error_msg = refresh_access_token()
    if not success or not access_token:
        return {
            "success": False,
            "post_id": None,
            "response": None,
            "error": error_msg
        }

    # Step 2: Build Post Payload & Headers
    post_url = format_location_url(loc_id, access_token=access_token)
    payload = build_post_payload(post_text, cta_action=cta_action, cta_url=cta_url)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    logger.info(f"Publishing post to GBP URL: {post_url}")

    # Step 3: Send POST request to Google Business Profile API
    try:
        response = requests.post(post_url, json=payload, headers=headers, timeout=20)
        try:
            response_data = response.json()
        except Exception:
            response_data = {"raw": response.text}

        if response.status_code in (200, 201):
            post_name = response_data.get("name") or response_data.get("id") or "published_ok"
            logger.info(f"Successfully published post to Google Business Profile: {post_name}")
            return {
                "success": True,
                "post_id": post_name,
                "response": response_data,
                "error": None
            }
        else:
            err_detail = response_data.get("error", {}).get("message") if isinstance(response_data.get("error"), dict) else response.text
            err_msg = f"GBP API Error ({response.status_code}): {err_detail}"
            logger.error(err_msg)
            return {
                "success": False,
                "post_id": None,
                "response": response_data,
                "error": err_msg
            }

    except requests.RequestException as e:
        err_msg = f"Network exception while publishing to GBP: {e}"
        logger.error(err_msg)
        return {
            "success": False,
            "post_id": None,
            "response": None,
            "error": err_msg
        }
