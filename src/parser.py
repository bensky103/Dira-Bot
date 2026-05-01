import json
import logging
from openai import OpenAI

from src.config import OPENAI_API_KEY
from src.geocoder import geocode_address

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are a real estate listing parser for the Israeli rental market.

Your job: extract structured data from Facebook posts about WHOLE apartments for rent.

GROUP CONTEXT — when the user message starts with a "Group name:" header, that is the
name of the Facebook group the post was scraped from. Treat it as a STRONG prior on
the city. Examples:
  - "דירות רמת גן", "להשכרה ברמת גן", "ramat gan apartments" → city is רמת גן
  - "דירות גבעתיים", "השכרה בגבעתיים" → city is גבעתיים
  - "דירות תל אביב", "tlv apartments" → city is תל אביב
The group is hyper-local: only override the group's city if the post body EXPLICITLY
names a different city (e.g. "Located in Givatayim, posted in TLV group by mistake").
Do NOT override based on a street name alone — many streets exist in multiple
adjacent cities (ביאליק, ז'בוטינסקי, ויצמן, etc.). When the street is ambiguous,
the group name wins.

CRITICAL — SKIP these types of posts (return {"skip": true}):
1. Shared apartments / roommate posts (דירת שותפים, שותף/ה, חדר בדירה משותפת, חדר בשותפות, מחפש/ת שותף/ה, room in shared apartment, רום מייט, חדר להשכרה בדירה, חדר פנוי בדירה)
2. Posts renting out a single room within an existing apartment (NOT a whole apartment)
3. Studio apartments (דירת סטודיו, סטודיו)
4. Someone looking/searching for an apartment (מחפש/ת דירה)
5. Questions, jokes, comments, group rules, spam, or unrelated content

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
  CRITICAL — city boundary rules (Tel Aviv / Ramat Gan / Givatayim are NOT interchangeable):
  • רמת גן streets: בארי, ביאליק (east of אבן גבירול), ז'בוטינסקי (east of נהר הירדן), הרואה, קריניצי, אלכסנדר פן, אבא הלל, חיים עוזר
  • גבעתיים streets: כצנלסון, בורוכוב, אפרים, שינקין (in גבעתיים context), סירקין, ויצמן (east section)
  • תל אביב streets: דיזנגוף, בן יהודה, אלנבי, רוטשילד, הירקון, אבן גבירול (west section), בוגרשוב, פרישמן, ארלוזורוב (west section), נמיר
  • If the post mentions a street that exists in multiple cities, use other context clues (neighborhood names, landmarks, nearby streets) to determine the correct city.
  • When unsure between adjacent cities, prefer the city explicitly mentioned in the post text. If no city is mentioned, do NOT default to תל אביב — try to infer from the street and area.
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


def parse_post(text: str, group_name: str = "") -> dict | None:
    """Send post text to OpenAI gpt-4o-mini and return parsed JSON or None.

    group_name: name of the Facebook group the post came from. Used as a strong
    city prior — see SYSTEM_PROMPT.
    """
    post_text = text[:3000]
    user_content = (
        f"Group name: {group_name}\n\n{post_text}" if group_name else post_text
    )

    logger.debug("--- Parsing post ---")
    logger.debug("Post preview: %s", post_text[:200].replace("\n", " | "))
    logger.debug("Full post text:\n%s", post_text)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
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

        # One Google Geocoding call per new listing — fills in coordinates and
        # the verified city for the map, and acts as the area fallback when the
        # LLM couldn't determine the neighborhood. Persisted in the sheet so
        # the Next.js map never has to call Google itself.
        lat = lng = None
        verified_city = ""
        if street and city:
            geo = geocode_address(street, city)
            if geo:
                lat = geo["lat"]
                lng = geo["lng"]
                verified_city = geo["verified_city"] or ""
                if (not area or area == "לא ידוע") and geo["area"]:
                    logger.info("  Geocoding fallback: area resolved to '%s'", geo["area"])
                    area = geo["area"]

        result = {
            "city": city,
            "area": area,
            "street": street,
            "price_nis": data.get("price_nis", 0),
            "rooms": data.get("rooms", 0),
            "sqm": data.get("sqm", 0),
            "phone": data.get("phone", ""),
            "is_catch": bool(data.get("is_catch", False)),
            "lat": lat if lat is not None else "",
            "lng": lng if lng is not None else "",
            "verified_city": verified_city,
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
