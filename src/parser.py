import json
import logging
from openai import OpenAI

from src.config import OPENAI_API_KEY
from src.geocoder import resolve_area

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are a real estate listing parser for the Israeli rental market.

Your job: extract structured data from Facebook posts about WHOLE apartments for rent.

CRITICAL — SKIP these types of posts (return {"skip": true}):
1. Shared apartments / roommate posts (דירת שותפים, שותף/ה, חדר בדירה משותפת, חדר בשותפות, מחפש/ת שותף/ה, room in shared apartment, רום מייט, חדר להשכרה בדירה, חדר פנוי בדירה)
2. Posts renting out a single room within an existing apartment (NOT a whole apartment)
3. Someone looking/searching for an apartment (מחפש/ת דירה)
4. Questions, jokes, comments, group rules, spam, or unrelated content

Indicators of a roommate/shared apartment post:
- Mentions "שותפים", "שותף", "שותפה", "שיתוף", "חדר בדירת"
- Describes a room in a shared living situation
- Mentions existing roommates or how many people live there
- Price is very low for the area (usually under 2500₪) and mentions a single room

ONLY extract data from posts offering a COMPLETE apartment for rent to a single tenant/family.
Do NOT skip a post just because the price is high, the location is unclear, or it mentions a broker.

When in doubt about whether it's a shared apartment — skip it.

Extract these fields:
- city: the city name in Hebrew (e.g. "תל אביב", "רמת גן"). If it says "צפון הישן" or similar neighborhood names, determine which city it's in.
- area: the neighborhood/area within the city in Hebrew. You MUST always determine this field — never return null.
  Infer from the street name, nearby landmarks, or any location hint in the post.
  IMPORTANT: The area must be a REAL neighborhood name (e.g. "צפון ישן", "פלורנטין", "נווה צדק", "הדר יוסף").
  Do NOT return descriptions like "שכונה שקטה", "מיקום מעולה", "ליד הים" — these are NOT area names.
  Tel Aviv examples: "דיזנגוף"/"בן יהודה"/"פרישמן" → "צפון ישן", "רוטשילד"/"שינקין"/"לילינבלום" → "לב העיר",
  "שדרות חן"/"כיכר רבין"/"אבן גבירול" → "צפון ישן", "פלורנטין"/"הרצל" → "פלורנטין",
  "ארלוזורוב"/"דרך נמיר"/"ז'בוטינסקי" → "הצפון החדש", "ישעיהו"/"הירקון"/"ירקון" → "צפון תל אביב",
  "יפתח"/"שושנה דמארי" → "יד אליהו", "סלמה"/"מנחם בגין" → "נווה שאנן".
  For other cities, use the commonly known neighborhood name.
  If you truly cannot determine the area from any clue, return "לא ידוע".
- street: street name in Hebrew, or null if not mentioned
- price_nis: monthly rent as integer. Parse "10,000 ₪" as 10000. Null if not mentioned.
- rooms: number of rooms as float (e.g. 2.5 for "שתיים וחצי"). "חד" = "חדרים". Null if not mentioned.
- sqm: size in square meters as integer. "מ״ר" or "מטר" = sqm. Null if not mentioned.
- phone: phone number in any format, null if not mentioned
- is_catch: true ONLY if the price seems significantly below market rate for the area and apartment size

Return strictly as JSON.
If the post is NOT a rental offering (or is a roommate/shared apartment listing), return {"skip": true}"""


def parse_post(text: str) -> dict | None:
    """Send post text to OpenAI gpt-4o-mini and return parsed JSON or None."""
    post_text = text[:3000]

    logger.debug("--- Parsing post ---")
    logger.debug("Post preview: %s", post_text[:200].replace("\n", " | "))
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
        logger.debug("  LLM response: %s", raw)
        data = json.loads(raw)

        if data.get("skip"):
            logger.info("  -> Skipped (not a listing)")
            return None

        area = data.get("area", "")
        street = data.get("street", "")
        city = data.get("city", "")

        # Fallback to geocoding if LLM couldn't determine the area
        if (not area or area == "לא ידוע") and street and city:
            geocoded_area = resolve_area(street, city)
            if geocoded_area:
                logger.info("  Geocoding fallback: area resolved to '%s'", geocoded_area)
                area = geocoded_area

        result = {
            "city": city,
            "area": area,
            "street": street,
            "price_nis": data.get("price_nis", 0),
            "rooms": data.get("rooms", 0),
            "sqm": data.get("sqm", 0),
            "phone": data.get("phone", ""),
            "is_catch": bool(data.get("is_catch", False)),
        }

        logger.info(
            "  -> Listing: %s, %s, %s | %s NIS | %s rooms | %s sqm | catch=%s",
            result["city"], result["area"], result["street"], result["price_nis"],
            result["rooms"], result["sqm"], result["is_catch"],
        )
        return result

    except Exception as e:
        logger.error("LLM parse error: %s", e)
        return None
