"""
Unit tests for ParentingHub Google Business Profile Agent.

Covers: sanitizer, pillar rotation, payloads, scraper image support, Make.com webhook payload,
Discord notifier with product image, and generator with product context.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import CONTENT_PILLARS, LOCATION_ID, CTA_ACTION, CTA_URL
from generator import sanitize_gbp_text, get_next_pillar, generate_post_content
from publisher import build_post_payload, format_location_url, publish_via_webhook
from scraper import get_featured_product, get_product_catalog, FALLBACK_CATALOG
from notifier import build_discord_embed, send_discord_report, BRAND_COLOR_INT


class TestGenerator(unittest.TestCase):
    def test_sanitize_gbp_text_removes_asterisks(self):
        markdown_text = (
            "**Heading in bold**\n"
            "*Italic text here*\n"
            "* Bullet item 1\n"
            "* Bullet item 2\n"
            "This is **critical** for *every* parent!"
        )
        cleaned = sanitize_gbp_text(markdown_text)
        self.assertNotIn("*", cleaned)
        self.assertIn("Heading in bold", cleaned)
        self.assertIn("• Bullet item 1", cleaned)
        self.assertIn("• Bullet item 2", cleaned)
        self.assertIn("This is critical for every parent!", cleaned)

    def test_sanitize_gbp_text_removes_headers_and_links(self):
        markdown_text = (
            "### Baby Sleep Routine Guide\n"
            "Check [ParentingHub](https://parentinghub.pk/) for more."
        )
        cleaned = sanitize_gbp_text(markdown_text)
        self.assertNotIn("###", cleaned)
        self.assertNotIn("[ParentingHub]", cleaned)
        self.assertIn("Baby Sleep Routine Guide", cleaned)
        self.assertIn("ParentingHub (https://parentinghub.pk/)", cleaned)

    def test_pillar_rotation_structure(self):
        self.assertEqual(len(CONTENT_PILLARS), 4)
        pillar_ids = [p["id"] for p in CONTENT_PILLARS]
        self.assertEqual(pillar_ids, ["learn", "shop", "track", "connect"])

    def test_generate_post_content_all_pillars(self):
        for pillar_id in ["learn", "shop", "track", "connect"]:
            result = generate_post_content(pillar_id=pillar_id)
            self.assertEqual(result["pillar_id"], pillar_id)
            self.assertTrue(len(result["content"]) > 50)
            self.assertNotIn("*", result["content"])
            self.assertNotIn("#", result["content"])

    def test_generate_post_with_product_context(self):
        """Test that product_context is accepted and the result includes product_link."""
        product = {
            "name": "Philips Avent Anti-Colic Bottle",
            "link": "https://parentinghub.pk/product/avent-anti-colic",
            "image_url": "https://www.parentinghub.pk/assets/feeder-b349f53c.png",
            "category": "Feeding Essentials",
            "description": "Clinically proven anti-colic vent system.",
        }
        result = generate_post_content(pillar_id="shop", product_context=product)
        self.assertEqual(result["pillar_id"], "shop")
        self.assertTrue(len(result["content"]) > 50)
        self.assertIn("product_link", result)


class TestPublisher(unittest.TestCase):
    def test_build_post_payload(self):
        summary = "Newborn tips for Pakistani parents."
        payload = build_post_payload(summary, cta_action="LEARN_MORE", cta_url="https://parentinghub.pk/")

        self.assertEqual(payload["languageCode"], "en")
        self.assertEqual(payload["topicType"], "STANDARD")
        self.assertEqual(payload["summary"], summary)
        self.assertEqual(payload["callToAction"]["actionType"], "LEARN_MORE")
        self.assertEqual(payload["callToAction"]["url"], "https://parentinghub.pk/")

    def test_format_location_url(self):
        url1 = format_location_url("locations/17062544117938448005", account_id="")
        self.assertEqual(url1, "https://mybusiness.googleapis.com/v4/locations/17062544117938448005/localPosts")

        url2 = format_location_url("17062544117938448005", account_id="")
        self.assertEqual(url2, "https://mybusiness.googleapis.com/v4/locations/17062544117938448005/localPosts")

        url3 = format_location_url("accounts/12345/locations/67890")
        self.assertEqual(url3, "https://mybusiness.googleapis.com/v4/accounts/12345/locations/67890/localPosts")

    @patch("publisher.requests.post")
    def test_publish_via_webhook_payload_with_image(self, mock_post):
        """publish_via_webhook should send summary, link, and image_url payload to Make.com."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "OK"
        mock_post.return_value = mock_resp

        res = publish_via_webhook(
            post_summary="Test post content",
            link="https://parentinghub.pk/product/test",
            image_url="https://www.parentinghub.pk/assets/feeder-b349f53c.png",
            webhook_url="https://hook.make.com/test",
        )
        self.assertTrue(res["success"])
        self.assertTrue(mock_post.called)
        sent_payload = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1].get("json")
        self.assertEqual(sent_payload["summary"], "Test post content")
        self.assertEqual(sent_payload["link"], "https://parentinghub.pk/product/test")
        self.assertEqual(sent_payload["image_url"], "https://www.parentinghub.pk/assets/feeder-b349f53c.png")


class TestScraper(unittest.TestCase):
    def test_fallback_catalog_not_empty(self):
        """Fallback catalog should contain at least 5 verified products."""
        self.assertGreaterEqual(len(FALLBACK_CATALOG), 5)

    def test_fallback_catalog_structure(self):
        """Each fallback product must have name, link, image_url, category, and description."""
        for product in FALLBACK_CATALOG:
            self.assertIn("name", product)
            self.assertIn("link", product)
            self.assertIn("image_url", product)
            self.assertIn("category", product)
            self.assertIn("description", product)
            self.assertTrue(len(product["name"]) > 3)
            self.assertTrue(product["link"].startswith("https://"))
            self.assertTrue(product["image_url"].startswith("https://"))

    def test_get_featured_product_returns_valid_dict(self):
        """get_featured_product must always return a dict with required keys including image_url."""
        product = get_featured_product()
        self.assertIsInstance(product, dict)
        self.assertIn("name", product)
        self.assertIn("link", product)
        self.assertIn("image_url", product)
        self.assertIn("category", product)
        self.assertTrue(len(product["name"]) > 0)
        self.assertTrue(product["image_url"].startswith("https://"))

    def test_get_product_catalog_returns_list(self):
        """get_product_catalog must return a non-empty list."""
        catalog = get_product_catalog()
        self.assertIsInstance(catalog, list)
        self.assertGreater(len(catalog), 0)


class TestDiscordNotifier(unittest.TestCase):
    def test_brand_color_value(self):
        """Brand colour #e8578a should convert to the correct integer."""
        self.assertEqual(BRAND_COLOR_INT, 0xE8578A)

    def test_build_discord_embed_structure(self):
        """Embed dict must have all required Discord Embed fields."""
        embed = build_discord_embed(
            product_name="Philips Avent Anti-Colic Bottle",
            product_url="https://parentinghub.pk/",
            post_text="Test mini-blog content for GBP.",
            image_url="https://www.parentinghub.pk/assets/feeder-b349f53c.png",
            pillar_name="Shop (Authentic Baby Essentials)",
        )
        self.assertIn("title", embed)
        self.assertIn("description", embed)
        self.assertIn("color", embed)
        self.assertIn("fields", embed)
        self.assertIn("footer", embed)
        self.assertIn("timestamp", embed)
        self.assertIn("image", embed)
        self.assertEqual(embed["image"]["url"], "https://www.parentinghub.pk/assets/feeder-b349f53c.png")
        self.assertEqual(embed["color"], BRAND_COLOR_INT)
        self.assertIn("Assalam-o-Alaikum", embed["title"])
        self.assertIn("Test mini-blog content", embed["description"])

    def test_embed_contains_product_info(self):
        """Embed fields must contain the product name and URL."""
        embed = build_discord_embed(
            product_name="Tommee Tippee Closer to Nature",
            product_url="https://parentinghub.pk/product/tommee-tippee",
            post_text="Some post text.",
            image_url="https://www.parentinghub.pk/assets/feeder-b349f53c.png",
        )
        field_values = " ".join(f["value"] for f in embed["fields"])
        self.assertIn("Tommee Tippee", field_values)
        self.assertIn("parentinghub.pk", field_values)

    def test_embed_pillar_field_optional(self):
        """When pillar_name is None, embed should still have at least 2 fields."""
        embed = build_discord_embed(
            product_name="Test Product",
            product_url="https://parentinghub.pk/",
            post_text="Content.",
            pillar_name=None,
        )
        self.assertGreaterEqual(len(embed["fields"]), 2)

    def test_embed_pillar_field_present(self):
        """When pillar_name is given, embed should have 3 fields."""
        embed = build_discord_embed(
            product_name="Test Product",
            product_url="https://parentinghub.pk/",
            post_text="Content.",
            pillar_name="Learn",
        )
        self.assertEqual(len(embed["fields"]), 3)
        pillar_field_values = [f["value"] for f in embed["fields"] if "Pillar" in f["name"]]
        self.assertIn("Learn", pillar_field_values)

    @patch("notifier.requests.post")
    def test_send_discord_report_calls_webhook(self, mock_post):
        """send_discord_report should POST to the webhook when URL is configured."""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        from notifier import send_discord_report, DISCORD_WEBHOOK_URL

        if DISCORD_WEBHOOK_URL:
            result = send_discord_report(
                product_name="Test Product",
                product_url="https://parentinghub.pk/",
                post_text="Test summary content.",
                image_url="https://www.parentinghub.pk/assets/feeder-b349f53c.png",
                pillar_name="Shop",
            )
            self.assertTrue(mock_post.called)
            call_args = mock_post.call_args
            body = call_args.kwargs.get("json") or call_args[1].get("json")
            self.assertIn("embeds", body)
            self.assertEqual(len(body["embeds"]), 1)
            self.assertIn("Assalam-o-Alaikum", body["embeds"][0]["title"])
            self.assertIn("image", body["embeds"][0])
            self.assertEqual(body["embeds"][0]["image"]["url"], "https://www.parentinghub.pk/assets/feeder-b349f53c.png")


if __name__ == "__main__":
    unittest.main()
