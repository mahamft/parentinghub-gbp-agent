"""
Dynamic Web Scraper for ParentingHub (parentinghub.pk).

Scrapes product listings from the live website. Falls back to a curated,
verified product catalog if the site is unreachable or the HTML structure changes.
"""

import random
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger("parentinghub.scraper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SITE_URL = "https://parentinghub.pk/"
SCRAPE_TIMEOUT = 12  # seconds
DEFAULT_IMAGE_URL = "https://www.parentinghub.pk/assets/feeder-b349f53c.png"

# ---------------------------------------------------------------------------
# Fallback Catalog: Verified products that are always available if the live
# site cannot be reached or parsed.
# ---------------------------------------------------------------------------
FALLBACK_CATALOG: List[Dict[str, Any]] = [
    {
        "name": "Philips Avent Anti-Colic Baby Bottle",
        "link": "https://parentinghub.pk/",
        "image_url": "https://www.parentinghub.pk/assets/feeder-b349f53c.png",
        "category": "Feeding Essentials",
        "description": (
            "Clinically proven AirFree vent system reduces colic, gas, and reflux. "
            "BPA-free, easy to assemble, and compatible with the Philips Avent range."
        ),
    },
    {
        "name": "Tommee Tippee Closer to Nature Feeding Bottle",
        "link": "https://parentinghub.pk/",
        "image_url": "https://www.parentinghub.pk/assets/feeder-b349f53c.png",
        "category": "Feeding Essentials",
        "description": (
            "Breast-like silicone teat for a natural latch. Anti-colic valve prevents "
            "excessive air intake. Trusted by millions of parents worldwide."
        ),
    },
    {
        "name": "BPA-Free Silicone Baby Teether",
        "link": "https://parentinghub.pk/",
        "image_url": "https://www.parentinghub.pk/assets/feeder-b349f53c.png",
        "category": "Teething & Soothing",
        "description": (
            "Soft, food-grade silicone teether designed for sore gums. Easy grip for "
            "tiny hands. Freezer-safe for extra cooling relief during teething."
        ),
    },
    {
        "name": "Philips Avent Electric Steam Sterilizer",
        "link": "https://parentinghub.pk/",
        "image_url": "https://www.parentinghub.pk/assets/feeder-b349f53c.png",
        "category": "Hygiene & Sterilization",
        "description": (
            "Eliminates 99.9% of harmful germs in just 6 minutes. Fits up to 6 bottles "
            "and accessories. Compact design for Pakistani kitchen countertops."
        ),
    },
    {
        "name": "Tommee Tippee Twist & Click Nappy Disposal Bin",
        "link": "https://parentinghub.pk/",
        "image_url": "https://www.parentinghub.pk/assets/feeder-b349f53c.png",
        "category": "Baby Care Essentials",
        "description": (
            "Multi-layer antibacterial film locks in odour. One-handed, twist-and-click "
            "mechanism for quick, hygienic nappy disposal."
        ),
    },
    {
        "name": "Baby Bath Thermometer & Safety Set",
        "link": "https://parentinghub.pk/",
        "image_url": "https://www.parentinghub.pk/assets/feeder-b349f53c.png",
        "category": "Bath & Safety",
        "description": (
            "Instant-read digital thermometer ensures the perfect bath temperature every "
            "time. Includes non-slip bath mat for added safety."
        ),
    },
    {
        "name": "Newborn Hospital Bag Essentials Kit",
        "link": "https://parentinghub.pk/",
        "image_url": "https://www.parentinghub.pk/assets/feeder-b349f53c.png",
        "category": "Maternity & Newborn",
        "description": (
            "All-in-one starter kit for expectant Pakistani moms: swaddle blankets, "
            "mittens, caps, cotton bibs, and a compact organiser pouch."
        ),
    },
    {
        "name": "Philips Avent Natural Response Teat Set",
        "link": "https://parentinghub.pk/",
        "image_url": "https://www.parentinghub.pk/assets/feeder-b349f53c.png",
        "category": "Feeding Accessories",
        "description": (
            "Natural Response technology releases milk only when baby actively drinks. "
            "Available in multiple flow rates for every growth stage."
        ),
    },
]


def _try_scrape_site() -> List[Dict[str, Any]]:
    """
    Attempt to scrape product data from the live parentinghub.pk website.

    Returns a list of product dicts, or an empty list on any failure.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("BeautifulSoup not installed; skipping live scrape.")
        return []

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        response = requests.get(SITE_URL, headers=headers, timeout=SCRAPE_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        products: List[Dict[str, Any]] = []

        # Strategy 1: Look for WooCommerce-style product cards
        product_cards = soup.select(".product, .product-card, .wc-block-grid__product")
        for card in product_cards:
            name_el = card.select_one(
                ".woocommerce-loop-product__title, .product-title, h2, h3"
            )
            link_el = card.select_one("a[href]")
            desc_el = card.select_one(
                ".product-description, .short-description, p"
            )
            cat_el = card.select_one(
                ".product-category, .product_cat, .posted_in a"
            )
            img_el = card.select_one("img[src], img[data-src], img[data-lazy-src]")

            if name_el and link_el:
                name = name_el.get_text(strip=True)
                link = link_el.get("href", SITE_URL)
                link = urljoin(SITE_URL, link)

                image_url = DEFAULT_IMAGE_URL
                if img_el:
                    raw_img = img_el.get("src") or img_el.get("data-src") or img_el.get("data-lazy-src")
                    if raw_img:
                        image_url = urljoin(SITE_URL, raw_img)

                products.append({
                    "name": name,
                    "link": link,
                    "image_url": image_url,
                    "category": cat_el.get_text(strip=True) if cat_el else "Baby Essentials",
                    "description": desc_el.get_text(strip=True) if desc_el else "",
                })

        # Strategy 2: If no WooCommerce cards, try generic product links
        if not products:
            all_links = soup.select("a[href*='product'], a[href*='shop']")
            for link_el in all_links[:10]:
                href = link_el.get("href", "")
                text = link_el.get_text(strip=True)
                if text and len(text) > 5 and href:
                    href = urljoin(SITE_URL, href)
                    img_el = link_el.select_one("img[src]") or link_el.find_parent().select_one("img[src]")
                    image_url = DEFAULT_IMAGE_URL
                    if img_el:
                        raw_img = img_el.get("src") or img_el.get("data-src")
                        if raw_img:
                            image_url = urljoin(SITE_URL, raw_img)

                    products.append({
                        "name": text,
                        "link": href,
                        "image_url": image_url,
                        "category": "Baby Essentials",
                        "description": "",
                    })

        if products:
            logger.info(f"Successfully scraped {len(products)} products from {SITE_URL}")
        else:
            logger.info("Live scrape returned no products; will use fallback catalog.")

        return products

    except requests.Timeout:
        logger.warning(f"Timeout while scraping {SITE_URL} (limit: {SCRAPE_TIMEOUT}s).")
        return []
    except requests.RequestException as e:
        logger.warning(f"Network error scraping {SITE_URL}: {e}")
        return []
    except Exception as e:
        logger.warning(f"Unexpected error during scrape: {e}")
        return []


def get_product_catalog() -> List[Dict[str, Any]]:
    """
    Return all available products, preferring live-scraped data with
    fallback catalog as a safety net.
    """
    live_products = _try_scrape_site()
    if live_products:
        return live_products
    logger.info("Using curated fallback product catalog.")
    return list(FALLBACK_CATALOG)


def get_featured_product() -> Dict[str, Any]:
    """
    Select one featured product for today's post.

    Returns:
        dict with keys: name, link, image_url, category, description
    """
    catalog = get_product_catalog()
    product = random.choice(catalog)

    # Guarantee all expected keys are present
    return {
        "name": product.get("name", "ParentingHub Baby Essential"),
        "link": product.get("link", SITE_URL),
        "image_url": product.get("image_url", DEFAULT_IMAGE_URL),
        "category": product.get("category", "Baby Essentials"),
        "description": product.get("description", ""),
    }


if __name__ == "__main__":
    import json

    print("=" * 60)
    print("🔍 ParentingHub Product Scraper - Test Run")
    print("=" * 60)
    featured = get_featured_product()
    print(json.dumps(featured, indent=2, ensure_ascii=False))
    print(f"\nFull catalog size: {len(get_product_catalog())} products")
    print("=" * 60)

