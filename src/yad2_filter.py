"""Policy filter for Yad2 listings — decides which raw API items to keep.

We only want long-term, whole-apartment rentals. Rejects:
  - Roommate listings   (structured flag: Partner_text == "לשותפים")
  - Studio-equivalents  (structured: HomeTypeID_text in {"סטודיו", "יחידת דיור"})
  - Sublets/short-term  (text fallback on search_text — sublets mostly
                         live on Yad2's /realestate/sublet endpoint which
                         we don't hit, so this is defense-in-depth)
  - Anything under the price floor (a proxy for "this is a room, not a flat")

The primary discriminators are Yad2's own enumerated fields, not text matching
— typos in free-text don't affect these. The text fallback only runs on items
the structured filter didn't already decide.
"""
import re

# HomeTypeID_text values we reject outright. These are enum values from Yad2,
# not free text, so exact string match is safe.
REJECTED_HOME_TYPES = {
    "סטודיו",
    "יחידת דיור",
    "דירת שותפים",
}

# Price floor in NIS. Anything below is almost certainly a single-room rental
# that slipped through category tagging (see choice b1 in spec).
MIN_PRICE_NIS = 3500

# Text fallback — runs only against search_text/address_more when structured
# fields don't flag the item. Patterns are intentionally conservative: each
# one must be specific enough that a false positive on a normal apartment is
# very unlikely.
#
# Hebrew notes:
#   \bשותפ matches שותפים / שותפה / שותף / שיתוף-adjacent words
#   סאבלט / סאב.?לט covers hyphen and space variants
#   "חדר ב" + {דירה,דירת,בית} catches "חדר בדירה משותפת" etc.
FALLBACK_PATTERNS = [
    re.compile(r"שותפ[יוהםת]"),              # שותפים/שותפה/שותף/שותפות
    re.compile(r"סאב[\s\-]?לט"),             # סאבלט / סאב-לט / סאב לט
    re.compile(r"חדר\s+ב(דירה|דירת|בית)"),   # "room in apartment/house"
    re.compile(r"לטווח\s+קצר"),              # short-term
    re.compile(r"לתקופה\s+קצרה"),            # short period
    re.compile(r"\bsublet\b", re.IGNORECASE),
    re.compile(r"\broommate\b", re.IGNORECASE),
    re.compile(r"\bairbnb\b", re.IGNORECASE),
]


def should_keep(item: dict) -> tuple[bool, str]:
    """Return (keep, reason). reason is a short tag suitable for logging."""
    # 1. Primary roommate filter — Yad2's own structured flag
    if (item.get("Partner_text") or "").strip() == "לשותפים":
        return False, "partner_flag"

    # 2. Home type allowlist — reject studio-equivalents explicitly
    home_type = (item.get("HomeTypeID_text") or "").strip()
    if home_type in REJECTED_HOME_TYPES:
        return False, f"home_type:{home_type}"

    # 3. Price floor (b1) — rejects obvious single-room listings
    price = _extract_price(item.get("price"))
    if price > 0 and price < MIN_PRICE_NIS:
        return False, f"price_below_floor:{price}"

    # 4. Text fallback — only if structured fields didn't decide.
    #    search_text is a long blob Yad2 builds for their search index;
    #    address_more is the free-form headline.
    haystack = " ".join(
        str(item.get(k) or "") for k in ("search_text", "address_more", "title_2")
    )
    for pat in FALLBACK_PATTERNS:
        if pat.search(haystack):
            return False, f"text_fallback:{pat.pattern}"

    return True, "ok"


def _extract_price(price_raw) -> int:
    """Convert Yad2's price string ('27,000 ₪' / 'לא צוין מחיר') to int. 0 if missing."""
    if price_raw is None:
        return 0
    digits = re.sub(r"[^\d]", "", str(price_raw))
    return int(digits) if digits else 0
