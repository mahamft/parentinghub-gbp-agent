"""
Discord Employee-Style Notifier for ParentingHub GBP Agent.

Sends daily staff-update–style reports as rich Discord Embed cards
to the configured webhook after each publishing run.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import requests

from config import DISCORD_WEBHOOK_URL, BRAND_NAME, WEBSITE_URL

logger = logging.getLogger("parentinghub.notifier")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ParentingHub brand colour (hex -> decimal for Discord embeds)
BRAND_COLOR_HEX = "#e8578a"
BRAND_COLOR_INT = int(BRAND_COLOR_HEX.lstrip("#"), 16)  # 15226762


def _validate_discord_config() -> bool:
    """Check whether the Discord webhook URL is present."""
    return bool(DISCORD_WEBHOOK_URL)


def _post_discord_webhook(payload: dict) -> dict:
    """
    Low-level helper: POST a JSON payload to the Discord webhook.

    Returns a result dict with 'ok' and optional 'error'.
    """
    if not _validate_discord_config():
        msg = "DISCORD_WEBHOOK_URL not configured in .env"
        logger.warning(msg)
        return {"ok": False, "error": msg}

    try:
        resp = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=15,
        )
        # Discord returns 204 No Content on success
        if resp.status_code in (200, 201, 204):
            logger.info("Discord notification sent successfully.")
            return {"ok": True}
        else:
            err = f"Discord webhook returned {resp.status_code}: {resp.text[:300]}"
            logger.error(err)
            return {"ok": False, "error": err}
    except requests.RequestException as e:
        err = f"Network error sending Discord webhook: {e}"
        logger.error(err)
        return {"ok": False, "error": err}


def send_discord_report(
    product_name: str,
    product_url: str,
    post_text: str,
    image_url: Optional[str] = None,
    pillar_name: Optional[str] = None,
    publishing_channel: str = "Make.com/Buffer",
    status: str = "SUCCESS",
) -> dict:
    """
    Send an employee-style daily report as a rich Discord Embed card with product image preview.

    Args:
        product_name:       Name of the featured product.
        product_url:        Direct link to the product / website.
        post_text:          Full mini-blog content that was published.
        image_url:          Product image URL for Discord preview card.
        pillar_name:        Content pillar used (Learn/Shop/Track/Connect).
        publishing_channel: How the post was published (Make.com, direct API, etc.).
        status:             Execution status string.

    Returns:
        Result dict with 'ok' bool and optional 'error' string.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Truncate post text for the embed description (Discord limit: 4096 chars)
    desc_text = post_text[:3900] if len(post_text) > 3900 else post_text

    status_display = "Live on Google Business Profile & Buffer" if publishing_channel == "Make.com/Buffer" else f"Published via {publishing_channel}"

    fields = [
        {
            "name": "🛍️ Featured Product",
            "value": f"[{product_name}]({product_url})",
            "inline": True,
        },
        {
            "name": "✅ Status",
            "value": status_display,
            "inline": True,
        },
    ]

    if pillar_name:
        fields.insert(1, {
            "name": "📂 Content Pillar",
            "value": pillar_name,
            "inline": True,
        })

    embed = {
        "title": "Assalam-o-Alaikum Ma'am! Aaj ka GBP Post Live Ho Gaya Hai 🚀",
        "description": f"```\n{desc_text}\n```",
        "color": BRAND_COLOR_INT,
        "fields": fields,
        "footer": {
            "text": f"{BRAND_NAME} • Discover • Connect • Grow 🤖",
        },
        "timestamp": timestamp,
        "url": product_url,
    }

    if image_url:
        embed["image"] = {"url": image_url}
        embed["thumbnail"] = {"url": image_url}

    payload = {
        "username": f"{BRAND_NAME} GBP Agent",
        "embeds": [embed],
    }

    return _post_discord_webhook(payload)


def send_discord_error_report(
    error_message: str,
    stage: str = "Publishing",
) -> dict:
    """
    Notify the Discord channel about a pipeline failure.

    Args:
        error_message: Description of what went wrong.
        stage:         Pipeline stage where the failure occurred.

    Returns:
        Result dict with 'ok' bool and optional 'error' string.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Truncate error for embed
    err_truncated = error_message[:1500] if len(error_message) > 1500 else error_message

    embed = {
        "title": f"⚠️ {BRAND_NAME} GBP Agent — Error Report",
        "description": f"An error occurred during **{stage}**.",
        "color": 0xFF4444,  # red
        "fields": [
            {
                "name": "❌ Stage",
                "value": stage,
                "inline": True,
            },
            {
                "name": "📛 Error Details",
                "value": f"```\n{err_truncated}\n```",
                "inline": False,
            },
            {
                "name": "🔄 Next Action",
                "value": "The agent will retry on the next scheduled run.",
                "inline": False,
            },
        ],
        "footer": {
            "text": f"{BRAND_NAME} • Discover • Connect • Grow 🤖",
        },
        "timestamp": timestamp,
    }

    payload = {
        "username": f"{BRAND_NAME} GBP Agent",
        "embeds": [embed],
    }

    return _post_discord_webhook(payload)


def build_discord_embed(
    product_name: str,
    product_url: str,
    post_text: str,
    image_url: Optional[str] = None,
    pillar_name: Optional[str] = None,
) -> dict:
    """
    Build and return the Discord embed dict without sending it.
    Useful for testing / inspection.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    desc_text = post_text[:3900] if len(post_text) > 3900 else post_text

    fields = [
        {"name": "🛍️ Featured Product", "value": f"[{product_name}]({product_url})", "inline": True},
        {"name": "✅ Status", "value": "Live on Google Business Profile & Buffer", "inline": True},
    ]
    if pillar_name:
        fields.insert(1, {"name": "📂 Content Pillar", "value": pillar_name, "inline": True})

    embed = {
        "title": "Assalam-o-Alaikum Ma'am! Aaj ka GBP Post Live Ho Gaya Hai 🚀",
        "description": f"```\n{desc_text}\n```",
        "color": BRAND_COLOR_INT,
        "fields": fields,
        "footer": {"text": f"{BRAND_NAME} • Discover • Connect • Grow 🤖"},
        "timestamp": timestamp,
        "url": product_url,
    }

    if image_url:
        embed["image"] = {"url": image_url}
        embed["thumbnail"] = {"url": image_url}

    return embed


if __name__ == "__main__":
    # Quick manual test
    result = send_discord_report(
        product_name="Philips Avent Anti-Colic Bottle",
        product_url="https://parentinghub.pk/",
        post_text=(
            "🍼 Colic Aur Gas Ki Pareshani? Philips Avent Anti-Colic Bottle Se "
            "Baby Ko Milega Instant Relief!\n\n"
            "• Clinically proven AirFree vent system\n"
            "• BPA-free aur easy to clean\n"
            "• 100% genuine, counterfeit-free guarantee\n\n"
            "Shop now at parentinghub.pk"
        ),
        pillar_name="Shop (Authentic Baby Essentials)",
    )
    print(f"Discord response: {result}")
