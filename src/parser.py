import json
import logging
from openai import OpenAI

from src.config import OPENAI_API_KEY, FILTERS

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)


def _build_system_prompt() -> str:
    """Build the system prompt dynamically from FILTERS config."""
    cities = FILTERS.get("cities")
    cities_str = ", ".join(cities) if cities else "any city"

    parts = []
    if FILTERS.get("min_rooms"):
        parts.append(f"at least {FILTERS['min_rooms']} rooms")
    if FILTERS.get("max_rooms"):
        parts.append(f"at most {FILTERS['max_rooms']} rooms")
    if FILTERS.get("min_sqm"):
        parts.append(f"at least {FILTERS['min_sqm']} sqm")
    if FILTERS.get("max_sqm"):
        parts.append(f"at most {FILTERS['max_sqm']} sqm")
    if FILTERS.get("max_price"):
        parts.append(f"max price {FILTERS['max_price']:,} NIS")
    if FILTERS.get("min_price"):
        parts.append(f"min price {FILTERS['min_price']:,} NIS")

    criteria = "; ".join(parts) if parts else "no specific criteria"

    return f"""You are a real estate listing parser for the Israeli rental market.

Your job: extract structured data from Hebrew Facebook posts about apartments for rent.

Target criteria: {cities_str} | {criteria}

For each post, determine:
1. Is this a rental listing? (not a "looking for" post, not a question, not spam, not a comment)
2. If yes, extract: city, street, price_nis (monthly rent as integer), rooms (float, e.g. 2.5), sqm (integer), phone
3. Set is_catch = true if the price is significantly below market rate for the area and size

Return strictly as JSON with these fields: city, street, price_nis, rooms, sqm, phone, is_catch
If the post is NOT a rental listing, return {{"skip": true}}

Important:
- Posts in Hebrew. City/street names should be in Hebrew as they appear.
- "חדרים" = rooms, "מ״ר" or "מטר" = sqm, "₪" or "ש״ח" = NIS
- If a field is not mentioned, use null
- Phone can be in any format"""


SYSTEM_PROMPT = _build_system_prompt()


def parse_post(text: str) -> dict | None:
    """Send post text to OpenAI gpt-4o-mini and return parsed JSON or None."""
    # Truncate to save tokens
    post_text = text[:3000]

    logger.info("--- Parsing post ---")
    logger.info("Post preview: %s", post_text[:200].replace("\n", " | "))
    logger.debug("Full post text:\n%s", post_text)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": post_text},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        logger.info("  LLM response: %s", raw)
        data = json.loads(raw)

        if data.get("skip"):
            logger.info("  -> Skipped (not a listing)")
            return None

        result = {
            "city": data.get("city", ""),
            "street": data.get("street", ""),
            "price_nis": data.get("price_nis", 0),
            "rooms": data.get("rooms", 0),
            "sqm": data.get("sqm", 0),
            "phone": data.get("phone", ""),
            "is_catch": bool(data.get("is_catch", False)),
        }

        logger.info(
            "  -> Listing: %s, %s | %s NIS | %s rooms | %s sqm | catch=%s",
            result["city"], result["street"], result["price_nis"],
            result["rooms"], result["sqm"], result["is_catch"],
        )
        return result

    except Exception as e:
        logger.error("LLM parse error: %s", e)
        return None
