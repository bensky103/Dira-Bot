import json
import logging
from openai import OpenAI

from src.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are a real estate listing parser for the Israeli rental market.

Your job: extract structured data from Facebook posts about apartments for rent.

IMPORTANT: You must extract data from ANY post that is offering an apartment/room/property for rent.
Do NOT skip a post just because the price is high, the location is unclear, or it mentions a broker.
The ONLY reason to skip is if the post is genuinely NOT a rental listing (e.g. someone looking for an apartment, a question, a joke, a comment, group rules, spam, or unrelated content).

When in doubt, extract the data — do not skip.

Extract these fields:
- city: the city name in Hebrew (e.g. "תל אביב", "רמת גן"). If it says "צפון הישן" or similar neighborhood names, determine which city it's in.
- street: street name in Hebrew, or null if not mentioned
- price_nis: monthly rent as integer. Parse "10,000 ₪" as 10000. Null if not mentioned.
- rooms: number of rooms as float (e.g. 2.5 for "שתיים וחצי"). "חד" = "חדרים". Null if not mentioned.
- sqm: size in square meters as integer. "מ״ר" or "מטר" = sqm. Null if not mentioned.
- phone: phone number in any format, null if not mentioned
- is_catch: true ONLY if the price seems significantly below market rate for the area and apartment size

Return strictly as JSON.
If the post is NOT a rental offering, return {"skip": true}"""


def parse_post(text: str) -> dict | None:
    """Send post text to OpenAI gpt-4o-mini and return parsed JSON or None."""
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
