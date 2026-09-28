"""
Main entry point and CLI interface for ParentingHub Google Business Profile Agent.

Usage:
  python main.py --test               # Run test mode (generates & displays sample post without publishing)
  python main.py --test --pillar shop # Test a specific content pillar (learn/shop/track/connect)
  python main.py --publish            # Generate & publish immediately to Google Business Profile
  python main.py --schedule           # Start weekly background scheduler
  python main.py --history            # View post history and current pillar rotation state
"""

import sys
import json
import logging
import argparse
from typing import Optional

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config import (
    BRAND_NAME,
    BRAND_DOMAIN,
    WEBSITE_URL,
    LOCATION_ID,
    CTA_ACTION,
    CTA_URL,
    SCHEDULE_DAY,
    SCHEDULE_TIME,
    CONTENT_PILLARS,
    validate_gemini_config,
    validate_gbp_config,
    validate_discord_config,
)
from generator import (
    generate_post_content,
    load_post_history,
    record_successful_post,
    get_next_pillar,
    sanitize_gbp_text,
)
from publisher import (
    publish_to_gbp,
    build_post_payload,
    format_location_url,
)
from scraper import get_featured_product
from notifier import send_discord_report, send_discord_error_report
from scheduler import start_scheduler, execute_daily_publishing_job

logger = logging.getLogger("parentinghub.main")


def test_run(pillar_id: Optional[str] = None, specific_topic: Optional[str] = None) -> dict:
    """
    Test Mode Function:
    Generates a sample post adhering to all ParentingHub brand guidelines,
    validates markdown absence and character counts, and prints the simulated
    Google Business Profile payload to the console WITHOUT publishing.
    """
    print("\n" + "=" * 70)
    print(f"✨  PARENTINGHUB ({BRAND_DOMAIN}) - GBP AGENT TEST MODE  ✨")
    print("=" * 70)

    # 1. Check Configuration
    gemini_ready = validate_gemini_config()
    gbp_ready = validate_gbp_config()
    discord_ready = validate_discord_config()

    print(f"• Gemini AI API Key:   {'✅ Configured' if gemini_ready else '⚠️  Missing in .env (Using Simulated Mode)'}")
    print(f"• Google OAuth2 GBP:   {'✅ Configured' if gbp_ready else '⚠️  Missing in .env (Publishing disabled)'}")
    print(f"• Discord Notifier:    {'✅ Configured' if discord_ready else '⚠️  Missing in .env (Notifications disabled)'}")
    print(f"• Target Location:     {LOCATION_ID}")
    print(f"• Call-to-Action:      {CTA_ACTION} -> {CTA_URL}")

    # 2. Fetch featured product via scraper (for shop pillar)
    product = None
    effective_pillar = pillar_id
    if not effective_pillar:
        next_p, _ = get_next_pillar()
        effective_pillar = next_p["id"]

    if effective_pillar == "shop":
        product = get_featured_product()
        print(f"\n🛍️  Scraped Product:    {product['name']} ({product['category']})")
        print(f"   Link:              {product['link']}")

    # 3. Generate Content
    post_data = generate_post_content(
        pillar_id=pillar_id,
        topic=specific_topic,
        product_context=product,
    )
    payload = build_post_payload(post_data["content"])

    # 4. Formatting Validation Checks
    has_markdown_asterisks = "*" in post_data["content"]
    has_markdown_headers = "#" in post_data["content"]
    word_count = post_data["word_count"]
    char_count = post_data["character_count"]

    print("\n" + "-" * 70)
    print(f"📌 CONTENT PILLAR: [{post_data['pillar_name'].upper()}]")
    print(f"🎯 TOPIC:          {post_data['topic']}")
    print(f"🤖 GENERATION:     {post_data['mode']} (Model: {post_data['model']})")
    print("-" * 70)

    print("\n📝 GENERATED POST TEXT FOR GOOGLE BUSINESS PROFILE:\n")
    print(post_data["content"])

    print("\n" + "-" * 70)
    print("🔍 GBP COMPLIANCE & VALIDATION:")
    print(f"• Plain Text (No Asterisks):   {'✅ PASS (Clean)' if not has_markdown_asterisks else '❌ FAIL (Asterisks found)'}")
    print(f"• No Markdown Headers (#):     {'✅ PASS (Clean)' if not has_markdown_headers else '❌ FAIL (Headers found)'}")
    print(f"• Character Count:             {char_count} chars (GBP limit: 1500)")
    print(f"• Word Count:                  {word_count} words (Ideal: 150-250)")

    print("\n📦 SIMULATED GBP API PAYLOAD (Ready for POST):")
    print(f"Endpoint: {format_location_url(LOCATION_ID)}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("=" * 70)
    print("ℹ️  This was a test run. Nothing was sent to Google Business Profile.\n")

    return post_data


def publish_pipeline(pillar_id: Optional[str] = None, specific_topic: Optional[str] = None) -> None:
    """
    Full autonomous publishing pipeline:
    1. Scrape a featured product + image URL from parentinghub.pk (with fallback catalog).
    2. Generate mini-blog content via Gemini AI, injecting product context.
    3. Dispatch to Make.com webhook with product link and image URL.
    4. On confirmed HTTP success (200/201/202/204), send employee-style Discord report with image preview.
    5. On publishing failure, log error and send failure alert to Discord.
    """
    logger.info("=" * 60)
    logger.info("Starting ParentingHub daily GBP publishing pipeline...")
    logger.info("=" * 60)

    product = None
    post_data = None

    try:
        # Step 1: Determine pillar and fetch product if needed
        effective_pillar = pillar_id
        if not effective_pillar:
            next_p, _ = get_next_pillar()
            effective_pillar = next_p["id"]

        if effective_pillar == "shop":
            logger.info("Shop pillar detected — fetching featured product from scraper...")
            product = get_featured_product()
            logger.info(f"Featured Product: {product['name']} ({product['category']})")
            logger.info(f"Image URL: {product['image_url']}")
        else:
            logger.info(f"Pillar: {effective_pillar} — no product scraping needed.")

        # Step 2: Generate content via Gemini
        post_data = generate_post_content(
            pillar_id=pillar_id,
            topic=specific_topic,
            product_context=product,
        )
        logger.info(f"Generated post for Pillar: {post_data['pillar_name']} ({post_data['pillar_id']})")
        logger.info(f"Topic: {post_data['topic']}")
        logger.info(f"Word count: {post_data['word_count']} | Char count: {post_data['character_count']}")

        # Step 3: Publish to Google Business Profile / Make.com Webhook with image_url
        product_link = product.get("link") if product else None
        product_image = product.get("image_url") if product else None

        pub_result = publish_to_gbp(
            post_data["content"],
            cta_url=product_link or CTA_URL,
            image_url=product_image,
        )

        # Step 4: Validate HTTP dispatch status
        if pub_result["success"]:
            logger.info("Post successfully published to Google Business Profile / Make.com webhook!")
            record_successful_post(post_data, gbp_response=pub_result.get("response"))
            logger.info("Pillar rotation advanced. Next pillar ready for tomorrow.")

            # Send success Discord notification with product image
            _send_success_notification(post_data, product)
        else:
            error_msg = pub_result.get("error", "Unknown publishing error")
            logger.error(f"Failed to publish post to GBP / Webhook: {error_msg}")
            send_discord_error_report(error_msg, stage="GBP Publishing Webhook")

    except Exception as e:
        logger.exception(f"Unexpected error in publishing pipeline: {e}")
        send_discord_error_report(str(e), stage="Pipeline Execution")


def _send_success_notification(post_data: dict, product: Optional[dict]) -> None:
    """Send the employee-style Discord report after a successful publish."""
    product_name = "ParentingHub Update"
    product_url = WEBSITE_URL
    image_url = "https://www.parentinghub.pk/assets/feeder-b349f53c.png"

    if product:
        product_name = product.get("name", product_name)
        product_url = product.get("link", product_url)
        image_url = product.get("image_url", image_url)

    send_discord_report(
        product_name=product_name,
        product_url=product_url,
        post_text=post_data.get("content", ""),
        image_url=image_url,
        pillar_name=post_data.get("pillar_name"),
    )


def show_history() -> None:
    """Display past post logs and next upcoming pillar."""
    history = load_post_history()
    next_pillar, next_idx = get_next_pillar()

    print("\n" + "=" * 65)
    print(f"📊 PARENTINGHUB POST HISTORY & ROTATION STATUS")
    print("=" * 65)
    print(f"Next Scheduled Pillar: [{next_idx + 1}/4] {next_pillar['name']}")
    print(f"Description:           {next_pillar['description']}")
    print(f"Automated Schedule:    Daily at {SCHEDULE_TIME}")

    posts = history.get("posts", [])
    print(f"\nTotal Logged Published Posts: {len(posts)}")
    if posts:
        print("\nRecent Published Posts:")
        for idx, post in enumerate(reversed(posts[-5:]), start=1):
            pub_time = post.get("published_at", "Unknown")
            print(f"  {idx}. [{post.get('pillar_id', '').upper()}] {post.get('topic', 'No topic')} ({pub_time})")
    else:
        print("  No posts have been published yet.")
    print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description=f"ParentingHub ({BRAND_DOMAIN}) - Automated Google Business Profile Agent"
    )
    parser.add_argument(
        "-t", "--test",
        action="store_true",
        help="Run in test mode: generate and validate a post without publishing"
    )
    parser.add_argument(
        "-p", "--publish",
        action="store_true",
        help="Generate a post for the next rotated pillar and publish immediately to GBP"
    )
    parser.add_argument(
        "-s", "--schedule",
        action="store_true",
        help="Start the daily automated background scheduler daemon"
    )
    parser.add_argument(
        "--pillar",
        choices=["learn", "shop", "track", "connect"],
        default=None,
        help="Specify or override a content pillar for test/publish"
    )
    parser.add_argument(
        "--topic",
        default=None,
        help="Specify a custom topic for post generation"
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Display post history and pillar rotation state"
    )

    args = parser.parse_args()

    # Default action if no flag is provided: run test_run()
    if len(sys.argv) == 1 or args.test:
        test_run(pillar_id=args.pillar, specific_topic=args.topic)
    elif args.publish:
        print("\n🚀 Executing immediate publish to Google Business Profile...")
        publish_pipeline(pillar_id=args.pillar, specific_topic=args.topic)
    elif args.schedule:
        start_scheduler()
    elif args.history:
        show_history()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
