import os
from dotenv import load_dotenv

load_dotenv()

# Persistent data directory: /data on Railway (volume), project root locally
DATA_DIR = "/data" if os.path.isdir("/data") else os.path.dirname(os.path.dirname(__file__))

# ── API Keys & Tokens ──
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_IDS = [
    cid.strip() for cid in os.environ["TELEGRAM_CHAT_IDS"].split(",") if cid.strip()
]
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Dira-Bot")

# ── Facebook Groups ──
# Comma-separated list of group URLs
GROUPS = [
    url.strip() for url in os.environ["FB_GROUPS"].split(",") if url.strip()
]

# ── Listing Filters ──
# All optional — omit or leave empty in .env to disable


def _int_or_none(key: str) -> int | None:
    val = os.getenv(key, "").strip()
    return int(val) if val else None


def _cities() -> list[str] | None:
    val = os.getenv("FILTER_CITIES", "").strip()
    if not val:
        return None
    return [c.strip() for c in val.split(",") if c.strip()]


FILTERS = {
    "min_rooms": _int_or_none("FILTER_MIN_ROOMS"),
    "max_rooms": _int_or_none("FILTER_MAX_ROOMS"),
    "min_sqm": _int_or_none("FILTER_MIN_SQM"),
    "max_sqm": _int_or_none("FILTER_MAX_SQM"),
    "max_price": _int_or_none("FILTER_MAX_PRICE"),
    "min_price": _int_or_none("FILTER_MIN_PRICE"),
    "cities": _cities(),
}

# ── Scraping Intervals ──
CYCLE_INTERVAL_SECONDS = int(os.getenv("CYCLE_MINUTES", "20")) * 60
GROUP_JITTER_BASE = 180  # seconds between groups
GROUP_JITTER_RANGE = 60  # +/- seconds

# ── Sheet Schema ──
SHEET_HEADERS = [
    "Timestamp", "City", "Street", "Price", "Rooms", "Size", "Phone", "Link", "Is Catch"
]
