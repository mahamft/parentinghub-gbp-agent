"""
Automated Daily Scheduler for ParentingHub GBP Social Media Agent.

Uses APScheduler to trigger the full publishing pipeline
(scrape -> generate -> publish -> notify) once per day.
"""

import sys
import time
import logging
from datetime import datetime
from typing import Optional

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import (
    SCHEDULE_DAY,
    SCHEDULE_TIME,
    CTA_URL,
    WEBSITE_URL,
    validate_gbp_config,
    validate_gemini_config,
    validate_discord_config,
)
from generator import (
    generate_post_content,
    record_successful_post,
    get_next_pillar,
)
from publisher import publish_to_gbp
from scraper import get_featured_product
from notifier import send_discord_report, send_discord_error_report

logger = logging.getLogger("parentinghub.scheduler")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def execute_daily_publishing_job() -> None:
    """
    Core job triggered by the scheduler:
    1. Fetches a featured product via scraper (with fallback catalog).
    2. Generates post content using Gemini for the next rotated pillar.
    3. Publishes the post to Google Business Profile (via Webhook or direct API).
    4. Records successful publication in history.
    5. Sends employee-style Discord report on success or error.
    """
    logger.info("=" * 60)
    logger.info("Starting daily scheduled ParentingHub GBP update job...")
    logger.info("=" * 60)

    product = None

    try:
        # Step 1: Determine next pillar and fetch product if shop pillar
        next_pillar, _ = get_next_pillar()
        effective_pillar_id = next_pillar["id"]

        if effective_pillar_id == "shop":
            logger.info("Shop pillar detected — fetching featured product from scraper...")
            product = get_featured_product()
            logger.info(f"Featured Product: {product['name']} ({product['category']})")

        # Step 2: Generate Content
        post_data = generate_post_content(product_context=product)
        logger.info(f"Generated post for Pillar: {post_data['pillar_name']} ({post_data['pillar_id']})")
        logger.info(f"Topic: {post_data['topic']}")
        logger.info(f"Word count: {post_data['word_count']} | Char count: {post_data['character_count']}")

        # Step 3: Publish to Google Business Profile
        product_link = product.get("link") if product else None
        pub_result = publish_to_gbp(
            post_data["content"],
            cta_url=product_link or CTA_URL,
        )

        if pub_result["success"]:
            logger.info("Post successfully published to Google Business Profile!")
            record_successful_post(post_data, gbp_response=pub_result.get("response"))
            logger.info("Pillar rotation advanced. Next pillar ready for tomorrow.")

            # Step 4: Send success Discord notification
            product_name = product.get("name", "ParentingHub Update") if product else "ParentingHub Update"
            product_url = product.get("link", WEBSITE_URL) if product else WEBSITE_URL

            send_discord_report(
                product_name=product_name,
                product_url=product_url,
                post_text=post_data.get("content", ""),
                pillar_name=post_data.get("pillar_name"),
            )
        else:
            error_msg = pub_result.get("error", "Unknown publishing error")
            logger.error(f"Failed to publish post to GBP: {error_msg}")
            send_discord_error_report(error_msg, stage="GBP Publishing")

    except Exception as e:
        logger.exception(f"Unexpected error during daily GBP publishing job: {e}")
        send_discord_error_report(str(e), stage="Scheduled Pipeline Execution")


# Keep backward compatibility alias
execute_weekly_publishing_job = execute_daily_publishing_job


def parse_schedule_time(time_str: str) -> tuple[int, int]:
    """Parse 'HH:MM' string into (hour, minute)."""
    try:
        parts = time_str.strip().split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return hour, minute
    except Exception:
        logger.warning(f"Invalid SCHEDULE_TIME '{time_str}', defaulting to 10:00.")
        return 10, 0


def day_name_to_cron_str(day_name: str) -> str:
    """Map day name string to 3-letter cron day format."""
    day_map = {
        "monday": "mon", "mon": "mon",
        "tuesday": "tue", "tue": "tue",
        "wednesday": "wed", "wed": "wed",
        "thursday": "thu", "thu": "thu",
        "friday": "fri", "fri": "fri",
        "saturday": "sat", "sat": "sat",
        "sunday": "sun", "sun": "sun",
    }
    return day_map.get(day_name.lower(), "mon")


def start_scheduler() -> None:
    """
    Start the blocking APScheduler to run the publishing job once per day.
    """
    hour, minute = parse_schedule_time(SCHEDULE_TIME)

    next_pillar, _ = get_next_pillar()

    logger.info("=" * 60)
    logger.info("ParentingHub Automated GBP Agent - Daily Scheduler Starting")
    logger.info(f"Schedule: DAILY at {hour:02d}:{minute:02d}")
    logger.info(f"Next upcoming pillar: {next_pillar['name']}")
    logger.info(f"Gemini AI Configured: {'Yes' if validate_gemini_config() else 'No (simulated fallback)'}")
    logger.info(f"GBP OAuth/Webhook Configured: {'Yes' if validate_gbp_config() else 'No'}")
    logger.info(f"Discord Notifier: {'Yes' if validate_discord_config() else 'No'}")
    logger.info("=" * 60)

    scheduler = BlockingScheduler()
    # Daily trigger: runs every day at the configured time
    trigger = CronTrigger(hour=hour, minute=minute)

    scheduler.add_job(
        execute_daily_publishing_job,
        trigger=trigger,
        id="parentinghub_gbp_daily",
        name="ParentingHub Daily GBP Publisher",
        replace_existing=True,
    )

    try:
        logger.info("Scheduler is running. Press Ctrl+C to exit.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user.")


if __name__ == "__main__":
    start_scheduler()
