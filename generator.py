"""
Content Generator module using Google Gemini API for ParentingHub (parentinghub.pk).

Rotates weekly content pillars:
1. Learn (Routines & Sleep)
2. Shop (Authentic Baby Essentials)
3. Track (Milestones & Growth)
4. Connect (Pakistani Parents Community)

Enforces strict plain-text formatting (no markdown asterisks or symbols) for Google Business Profile.
"""

import json
import re
import random
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

# Try importing the new google-genai SDK first, fall back to google-generativeai
GENAI_SDK_TYPE = None
try:
    from google import genai
    from google.genai import types
    GENAI_SDK_TYPE = "genai"
except ImportError:
    try:
        import google.generativeai as legacy_genai
        GENAI_SDK_TYPE = "legacy_genai"
    except ImportError:
        GENAI_SDK_TYPE = None

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    GEMINI_FALLBACK_MODELS,
    CONTENT_PILLARS,
    BRAND_NAME,
    BRAND_DOMAIN,
    WEBSITE_URL,
    TAGLINES,
    TARGET_AUDIENCE,
    TONE_OF_VOICE,
    HISTORY_FILE,
    BLOG_PRODUCT_PROMPT,
    validate_gemini_config,
)

logger = logging.getLogger("parentinghub.generator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def load_post_history() -> Dict[str, Any]:
    """Load posting history from disk."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not read history file ({e}), initializing fresh history.")
    return {"last_pillar_index": -1, "posts": []}


def save_post_history(history: Dict[str, Any]) -> None:
    """Save posting history to disk."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save post history: {e}")


def get_next_pillar(override_pillar_id: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
    """
    Determine the next content pillar to rotate to.
    If override_pillar_id is given, returns that specific pillar.
    """
    if override_pillar_id:
        for idx, pillar in enumerate(CONTENT_PILLARS):
            if pillar["id"].lower() == override_pillar_id.lower():
                return pillar, idx
        logger.warning(f"Unknown pillar '{override_pillar_id}', defaulting to normal rotation.")

    history = load_post_history()
    last_idx = history.get("last_pillar_index", -1)
    next_idx = (last_idx + 1) % len(CONTENT_PILLARS)
    return CONTENT_PILLARS[next_idx], next_idx


def sanitize_gbp_text(text: str) -> str:
    """
    Sanitize text specifically for Google Business Profile:
    - Removes all markdown asterisks (**bold**, *italic*, list *)
    - Removes markdown headings (#, ##, ###)
    - Removes markdown links [text](url) -> text (url)
    - Replaces markdown bullets with clean unicode bullets (•)
    - Strips code backticks
    - Cleans duplicate whitespace and ensures clean paragraph breaks
    """
    if not text:
        return ""

    # Replace markdown links [label](url) with "label (url)"
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)

    # Remove bold/italic markdown (**text**, *text*, __text__, _text_)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)

    # Remove markdown headers (# Header -> Header)
    text = re.sub(r'^\s{0,3}#{1,6}\s*', '', text, flags=re.MULTILINE)

    # Replace markdown bullet points (* item or - item) with unicode bullet (• item)
    text = re.sub(r'^\s*[\*\-]\s+', '• ', text, flags=re.MULTILINE)

    # Strip any remaining stray asterisks or backticks
    text = text.replace('`', '').replace('*', '')

    # Normalize excessive blank lines (max 2 consecutive newlines)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def build_system_instruction() -> str:
    """Construct the system prompt for the Gemini AI Model."""
    tagline_str = " | ".join(TAGLINES)
    return f"""You are the official social media brand voice for {BRAND_NAME} ({BRAND_DOMAIN}).
Taglines: {tagline_str}
Website: {WEBSITE_URL}
Target Audience: {TARGET_AUDIENCE}
Tone of Voice: {TONE_OF_VOICE}

CRITICAL FORMATTING RULES FOR GOOGLE BUSINESS PROFILE:
1. Google Business Profile DOES NOT SUPPORT MARKDOWN.
2. ABSOLUTELY DO NOT use asterisks for bolding (e.g. NEVER write **word** or *word*).
3. ABSOLUTELY DO NOT use hashtags (#) as markdown headings.
4. For bullet lists, use the unicode bullet symbol (•) or numbers (1., 2., 3.).
5. Include relevant, friendly emojis for visual appeal (🌙, 🍼, 👶, 🤍, ✨, 🛍️, 📊).
6. Length: Keep the post engaging and concise, between 150 and 260 words (ideal for Google Business Profile update posts).
7. Language: A natural, reassuring, and fluent blend of Roman Urdu and conversational English commonly spoken by modern Pakistani mothers (e.g., phrases like "Baby ki sleep routine", "Colic aur gas ki pareshani", "Naye parents ke liye", "Authentic feeding essentials").
8. Always end with a warm closing and a clear invitation to explore {BRAND_NAME} at {BRAND_DOMAIN} / {WEBSITE_URL}.
"""


def build_prompt_for_pillar(
    pillar: Dict[str, Any],
    specific_topic: Optional[str] = None,
    product_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Build the specific user prompt for the given pillar, optionally injecting live product context."""
    topic = specific_topic or random.choice(pillar["sample_topics"])
    keywords_str = ", ".join(pillar["keywords"])

    pillar_guidelines = {
        "learn": (
            "Focus on practical newborn/toddler routine advice, sleep tips, or soothing guidance. "
            "Acknowledge the exhausting realities of early parenting in Pakistan with deep empathy. "
            "Provide 2-3 actionable, gentle tips."
        ),
        "shop": (
            "Write a high-converting, educational mini-blog post for Google Business Profile highlighting an authentic baby product from ParentingHub. "
            "Structure the post EXACTLY as follows:\n"
            "(1) Catchy Headline addressing a real parent pain-point (e.g. colic, feeding, teething).\n"
            "(2) Problem intro (2-3 sentences validating parents' concerns).\n"
            "(3) Product Introduction (clearly name the product).\n"
            "(4) Key Benefits (3-4 bullet points using '•' detailing how the product solves the problem).\n"
            "(5) Authenticity Trust Factor (Highlight ParentingHub's 100% genuine, counterfeit-free guarantee).\n"
            "(6) Direct Call-to-Action with the product link."
        ),
        "track": (
            "Focus on tracking child milestones, feeding schedules, diaper counts, and growth checks. "
            "Reassure parents that every child develops at their own unique pace, but staying organized brings peace of mind. "
            "Share simple milestone checkpoints."
        ),
        "connect": (
            "Focus on parent community, fighting postpartum loneliness, and celebrating small daily wins. "
            "Remind Pakistani mothers and fathers that 'Parenting is easier when you don't do it alone.' "
            "Ask an engaging question to invite thoughts and foster connection."
        )
    }

    guidance = pillar_guidelines.get(pillar["id"], "Provide helpful, authentic parenting guidance.")

    # Inject live product context for shop pillar
    product_block = ""
    if product_context and pillar["id"] == "shop":
        p_name = product_context.get("name", "")
        p_link = product_context.get("link", "https://parentinghub.pk/")
        p_desc = product_context.get("description", "")
        p_cat = product_context.get("category", "Baby Essentials")
        topic = f"Mini-Blog Spotlight: {p_name}" if p_name else topic
        product_block = (
            f"\nFeatured Product Details (USE these in your post):\n"
            f"  Product Name: {p_name}\n"
            f"  Category: {p_cat}\n"
            f"  Description: {p_desc}\n"
            f"  Product Link: {p_link}\n"
            f"  Use the exact product link above as the CTA link in your post.\n"
        )

    return f"""Create a Google Business Profile update post for the '{pillar['name']}' weekly content pillar.

Theme/Topic: {topic}
Key Pillar Guidance: {guidance}
Keywords to weave naturally: {keywords_str}
{product_block}
Remember:
- NO markdown asterisks (no **bold**, no *italic*). Use standard capitalization or quotes for emphasis if needed.
- Write in an authentic, comforting Roman Urdu + English conversational blend for Pakistani parents.
- Keep within 150-250 words and strictly under 1,400 characters.
- Include a clear call-to-action mentioning ParentingHub ({BRAND_DOMAIN}).
"""


def generate_post_content(
    pillar_id: Optional[str] = None,
    topic: Optional[str] = None,
    product_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a complete GBP post using Google Gemini API.
    Returns a dictionary containing post metadata and sanitized content.

    If product_context is provided (from scraper), it is injected into the
    prompt for shop-pillar posts.
    """
    pillar, pillar_idx = get_next_pillar(pillar_id)

    if not validate_gemini_config():
        logger.warning("GEMINI_API_KEY not found in environment. Generating a high-quality simulated post.")
        return _generate_simulated_post(pillar, pillar_idx, topic, product_context=product_context)

    models_to_try = [GEMINI_MODEL] + [m for m in GEMINI_FALLBACK_MODELS if m != GEMINI_MODEL]
    raw_text = ""
    used_model = GEMINI_MODEL

    for candidate_model in models_to_try:
        try:
            system_inst = build_system_instruction()
            user_prompt = build_prompt_for_pillar(pillar, topic, product_context=product_context)

            if GENAI_SDK_TYPE == "genai":
                client = genai.Client(api_key=GEMINI_API_KEY)
                response = client.models.generate_content(
                    model=candidate_model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_inst,
                        temperature=GEMINI_TEMPERATURE,
                        max_output_tokens=2048,
                    )
                )
                raw_text = response.text if response and response.text else ""
                used_model = candidate_model
                break
            elif GENAI_SDK_TYPE == "legacy_genai":
                legacy_genai.configure(api_key=GEMINI_API_KEY)
                model = legacy_genai.GenerativeModel(
                    model_name=candidate_model,
                    system_instruction=system_inst,
                    generation_config={
                        "temperature": GEMINI_TEMPERATURE,
                        "max_output_tokens": 2048,
                    }
                )
                response = model.generate_content(user_prompt)
                raw_text = response.text if response and response.text else ""
                used_model = candidate_model
                break
            else:
                logger.error("No Gemini SDK installed.")
                return _generate_simulated_post(pillar, pillar_idx, topic, product_context=product_context)
        except Exception as e:
            logger.warning(f"Generation attempt with model '{candidate_model}' failed: {e}. Trying fallback model...")
            continue

    if not raw_text:
        logger.error("All Gemini API model attempts failed. Falling back to template generation.")
        return _generate_simulated_post(pillar, pillar_idx, topic, product_context=product_context)

    cleaned_text = sanitize_gbp_text(raw_text)

    # Store product context info in result if available
    product_link = ""
    if product_context:
        product_link = product_context.get("link", "")

    result = {
        "pillar_id": pillar["id"],
        "pillar_name": pillar["name"],
        "pillar_index": pillar_idx,
        "topic": topic or pillar["sample_topics"][0],
        "content": cleaned_text,
        "summary": cleaned_text,
        "raw_content": raw_text,
        "character_count": len(cleaned_text),
        "word_count": len(cleaned_text.split()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": used_model,
        "mode": "gemini_api",
        "product_link": product_link,
    }
    return result


def _generate_simulated_post(
    pillar: Dict[str, Any],
    pillar_idx: int,
    topic: Optional[str] = None,
    product_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Fallback / offline simulated post generator respecting all brand and formatting rules.
    """
    pillar_templates = {
        "learn": (
            "🌙 Newborn Sleep Routine Tips for Pakistani Moms\n\n"
            "Baby ko sulana initial months mein thora overwhelming lag sakta hai, especially jab sleep cycles unpredictable hon. "
            "Lekin aik gentle, consistent routine se baby ko settle hone mein bohot madad milti hai.\n\n"
            "• Dim Lights & Quiet Environment: Maghrib ke baad room ki lights dim rakhein taake baby ko day aur night ka farq samajh aye.\n"
            "• Soothing Pre-Sleep Bath & Massage: Halke warm paani se bath ya gentle massage baby ko instantly relax karta hai.\n"
            "• Swaddle & White Noise: Gentle swaddling newborn ko cozy aur secure feel karwati hai.\n\n"
            "Yaad rakhein, har baby apni pace par adjust hota hai. Parenting is easier when you don’t do it alone.\n\n"
            "Discover more newborn routines and parenting advice at parentinghub.pk"
        ),
        "shop": (
            "🍼 Authentic Feeding Gear: Say Goodbye to Colic & Gas\n\n"
            "Naye parents ke liye baby ki feeding routine smooth banana sab se important priority hoti hai. "
            "Colic aur gas ki wajah se baby aksar uncomfortable aur fussy ho jata hai, jisse sleep bhi disturb hoti hai.\n\n"
            "• Philips Avent Anti-Colic Bottles: Clinically proven airflex vent system jo air ko baby ke pait mein jane se rokta hai.\n"
            "• Tommee Tippee Closer to Nature: Breast-like teat for easy latch and smooth transition between breast & bottle.\n"
            "• 100% Genuine & BPA-Free: ParentingHub par aapko milti hain sirf 100% original, verified baby feeding essentials.\n\n"
            "Authentic baby care products with fast doorstep delivery across Pakistan.\n\n"
            "Shop verified baby essentials today at parentinghub.pk"
        ),
        "track": (
            "📊 Tracking Baby Milestones: Celebrate Every Little Step\n\n"
            "First smile se le kar first steps tak, baby ka growth journey har Pakistani parent ke liye bohot special hota hai. "
            "Milestones aur daily habits track karna aapko peace of mind deta hai.\n\n"
            "• 0-3 Months: Eye tracking, gentle smiles, aur neck control during tummy time.\n"
            "• 4-6 Months: Rolling over, babbling sounds, aur grabbing toys.\n"
            "• Feeding & Vaccination Logs: Keeping record of feeds, wet diapers, and immunizations ensures baby stays healthy.\n\n"
            "Har bacha unique hota hai, so never compare! Focus on gentle progress.\n\n"
            "Discover milestone guides and parenting tracking tools at parentinghub.pk"
        ),
        "connect": (
            "🤍 You Are Not Alone: Connecting Pakistani Parents\n\n"
            "Postpartum recovery aur initial parenting phase bohot khubsurat hone ke sath sath exhausting bhi ho sakta hai. "
            "Pakistani mothers and fathers often need a safe, supportive space to ask questions without judgment.\n\n"
            "• Share Your Journey: Late night feeds hon ya teething troubles, thousands of parents are going through the exact same phase.\n"
            "• Ask & Learn: From weaning advice to pediatrician recommendations, learn from real mom experiences.\n\n"
            "Tagline: Parenting is easier when you don’t do it alone.\n\n"
            "Join the conversation and connect with supportive parents across Pakistan at parentinghub.pk"
        )
    }

    content = sanitize_gbp_text(pillar_templates.get(pillar["id"], pillar_templates["learn"]))
    product_link = product_context.get("link", "") if product_context else ""

    return {
        "pillar_id": pillar["id"],
        "pillar_name": pillar["name"],
        "pillar_index": pillar_idx,
        "topic": topic or pillar["sample_topics"][0],
        "content": content,
        "summary": content,
        "raw_content": content,
        "character_count": len(content),
        "word_count": len(content.split()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": "simulated_brand_template",
        "mode": "fallback_simulated",
        "product_link": product_link,
    }


def record_successful_post(post_data: Dict[str, Any], gbp_response: Optional[Dict[str, Any]] = None) -> None:
    """Record a successfully published post to the history file to update the pillar rotation."""
    history = load_post_history()
    history["last_pillar_index"] = post_data.get("pillar_index", 0)
    history["last_published_at"] = datetime.now(timezone.utc).isoformat()
    history["posts"].append({
        "pillar_id": post_data.get("pillar_id"),
        "pillar_name": post_data.get("pillar_name"),
        "topic": post_data.get("topic"),
        "published_at": datetime.now(timezone.utc).isoformat(),
        "character_count": post_data.get("character_count"),
        "gbp_response": gbp_response or {}
    })
    # Keep last 50 entries
    if len(history["posts"]) > 50:
        history["posts"] = history["posts"][-50:]
    save_post_history(history)


def generate_product_blog(
    product_name: Optional[str] = None,
    product_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate an educational, high-converting mini-blog product post for Google Business Profile
    following BLOG_PRODUCT_PROMPT guidelines.

    If product_context dict is provided (from scraper), it is injected into the
    Gemini prompt so the AI writes about the exact scraped product.
    """
    selected_topic = f"Mini-Blog Spotlight: {product_name}" if product_name else None
    return generate_post_content(
        pillar_id="shop",
        topic=selected_topic,
        product_context=product_context,
    )


class ContentGenerator:
    """Convenience class wrapper for generating brand-compliant content."""

    def __init__(self):
        pass

    def generate_post(
        self,
        pillar: Optional[str] = None,
        topic: Optional[str] = None,
        product_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a post for a specific pillar or default rotation."""
        return generate_post_content(
            pillar_id=pillar, topic=topic, product_context=product_context
        )

    def generate_product_blog(
        self,
        product_name: Optional[str] = None,
        product_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a high-converting educational mini-blog product post."""
        return generate_product_blog(
            product_name=product_name, product_context=product_context
        )
