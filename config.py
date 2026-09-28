"""
Configuration loader and validator for ParentingHub GBP Social Media Agent.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
HISTORY_FILE = DATA_DIR / "post_history.json"

# Load environment variables from .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Brand Guidelines & Information
BRAND_NAME = "ParentingHub"
BRAND_DOMAIN = "parentinghub.pk"
WEBSITE_URL = "https://parentinghub.pk/"
TAGLINES = [
    "Parenting is easier when you don’t do it alone.",
    "Discover • Connect • Grow",
]
TARGET_AUDIENCE = (
    "Pakistani expectant & first-time mothers, and modern organized parents "
    "looking for trusted guidance and authentic baby care products."
)
TONE_OF_VOICE = (
    "Reassuring, welcoming, empathetic, practical, written in an engaging clean Roman Urdu & English blend."
)

# Core Content Pillars (Rotated Weekly)
CONTENT_PILLARS = [
    {
        "id": "learn",
        "name": "Learn (Child-care & Routines)",
        "description": "Practical newborn & toddler routines, sleep tips, soothing methods, and pediatric-friendly guidance.",
        "sample_topics": [
            "Newborn sleep routine tips & soothing techniques (Roman Urdu & English)",
            "Burping techniques & colic relief for first-time Pakistani mothers",
            "Starting solids (weaning foods) safely for 6+ month babies",
            "Gentle bedtime routine habits to help toddlers sleep through the night",
            "Dealing with toddler temper tantrums with positive parenting patience"
        ],
        "keywords": ["newborn sleep", "colic relief", "feeding routine", "soothing baby", "pakistani moms"]
    },
    {
        "id": "shop",
        "name": "Shop (Authentic Baby Essentials)",
        "description": "Highlighting authentic, verified baby essentials (such as Philips Avent and Tommee Tippee anti-colic feeding gear) available at parentinghub.pk.",
        "sample_topics": [
            "Why anti-colic feeding bottles (Philips Avent & Tommee Tippee) prevent gas & fussiness",
            "How to choose the right teat flow and authentic feeding accessories in Pakistan",
            "Hospital bag essentials checklist for expectant Pakistani moms",
            "Safe, BPA-free sterilizing & bottle care essentials at ParentingHub",
            "Top authentic newborn gear checklist to avoid counterfeit products"
        ],
        "keywords": ["Philips Avent Pakistan", "Tommee Tippee anti-colic", "authentic baby products", "baby gear shop", "parentinghub.pk"]
    },
    {
        "id": "track",
        "name": "Track (Milestones & Growth)",
        "description": "Child milestones, feeding, and growth tracking tools for organized parents.",
        "sample_topics": [
            "Month-by-month motor skills & speech milestones (0-12 months)",
            "Tracking baby's feeding and wet diaper counts in the first few weeks",
            "Vaccination schedule tracking & post-vaccine soothing care in Pakistan",
            "Tummy time progression & physical milestone checkpoints",
            "Growth spurt signs: why baby is suddenly cluster feeding & sleeping more"
        ],
        "keywords": ["baby milestones", "growth tracker", "feeding log", "vaccination guide pakistan", "child development"]
    },
    {
        "id": "connect",
        "name": "Connect (Community & Peer Support)",
        "description": "Community discussions and peer support for parents across Pakistan.",
        "sample_topics": [
            "Motherhood isolation vs. community: why Pakistani moms need a safe support space",
            "Asking fellow moms: how did you manage post-partum recovery with family?",
            "First-time parent anxiety: you are doing better than you think!",
            "Sharing your weekly parenting win or funny toddler moment with the community",
            "Connecting with local Pakistani moms navigating identical parenting phases"
        ],
        "keywords": ["mom community pakistan", "parenting support", "first-time mom group", "peer advice", "parentinghub family"]
    }
]

# Educational Mini-Blog Product Copywriting Prompt Template
BLOG_PRODUCT_PROMPT = """
You are a senior parenting advisor and e-commerce copywriter for ParentingHub (parentinghub.pk).
Write a high-converting, educational mini-blog post for Google Business Profile.

Guidelines:
1. Select ONE specific baby product from the store catalog (e.g., Philips Avent Anti-Colic Bottle, Tommee Tippee Feeding Set, BPA-Free Teethers, Sterilizers, Baby Care Kits).
2. Structure the post in a proper Mini-Blog Format:
   - Catchy Title addressing a real parent pain-point (e.g., baby colic, teething pain, feeding issues).
   - Problem intro (2-3 sentences validating parents' concerns).
   - Product Introduction (Name the product clearly).
   - Key Benefits (3-4 bullet points detailing how the product solves the problem).
   - Authenticity Trust Factor (Highlight ParentingHub's 100% genuine, counterfeit-free guarantee).
   - Direct Call-to-Action with the website link: https://parentinghub.pk/
3. Language: Engaging blend of Roman Urdu and English natural to Pakistani parents.
4. Total length: Under 1,400 characters (GBP post safe limit).
"""

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
GEMINI_TEMPERATURE = float(os.getenv("GEMINI_TEMPERATURE", "0.7"))
GEMINI_FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest", "gemini-1.5-flash", "gemini-2.5-flash"]

# Google Business Profile (GBP) API & OAuth2 Configuration
CLIENT_ID = os.getenv("CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "").strip()
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN", "").strip()
ACCOUNT_ID = os.getenv("ACCOUNT_ID", "").strip()
LOCATION_ID = os.getenv("LOCATION_ID", "locations/17062544117938448005").strip()

# GBP Post Defaults
CTA_ACTION = os.getenv("CTA_ACTION", "LEARN_MORE").strip()
CTA_URL = os.getenv("CTA_URL", WEBSITE_URL).strip()

# Scheduling Settings
SCHEDULE_DAY = os.getenv("SCHEDULE_DAY", "monday").strip().lower()
SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "10:00").strip()  # Format HH:MM 24hr

# Make.com / Buffer Webhook Integration
GBP_WEBHOOK_URL = os.getenv("GBP_WEBHOOK_URL", "").strip()

# Discord Webhook Notifier Configuration
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

# System / Mode
DEBUG = os.getenv("DEBUG", "false").strip().lower() in ("1", "true", "yes")


def validate_gemini_config() -> bool:
    """Check if Gemini credentials are configured."""
    return bool(GEMINI_API_KEY)


def validate_gbp_config() -> bool:
    """Check if Google Business Profile OAuth credentials or Webhook URL are configured."""
    has_oauth = bool(CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN and LOCATION_ID)
    has_webhook = bool(GBP_WEBHOOK_URL)
    return has_oauth or has_webhook


def validate_webhook_config() -> bool:
    """Check if Make.com / Buffer Webhook URL is configured."""
    return bool(GBP_WEBHOOK_URL)


def validate_discord_config() -> bool:
    """Check if Discord Webhook URL is configured."""
    return bool(DISCORD_WEBHOOK_URL)
