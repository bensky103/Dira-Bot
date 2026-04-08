import os
from dotenv import load_dotenv

load_dotenv()

# Persistent data directory (project root)
DATA_DIR = os.path.dirname(os.path.dirname(__file__))

# ── API Keys & Tokens (still from .env — these are secrets) ──
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_IDS = [
    cid.strip() for cid in os.environ["TELEGRAM_CHAT_IDS"].split(",") if cid.strip()
]
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Dira-Bot")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# ── Facebook Groups ──
GROUPS = [
    "https://www.facebook.com/groups/287564448778602/", #צפון תל אביב התחלה
    "https://www.facebook.com/groups/196649476429218/",
    "https://www.facebook.com/groups/telavivrentals/", #צפון תל אביב סוף
    "https://www.facebook.com/groups/647901439404148/", #רמת גן גבעתיים התחלה
    "https://www.facebook.com/groups/253957624766723/",
    "https://www.facebook.com/groups/402682483445663/",
    "https://www.facebook.com/groups/1774413905909921/",
    "https://www.facebook.com/groups/1456553661265604",
    "https://www.facebook.com/groups/1870209196564360/",
    "https://www.facebook.com/groups/1424244737803677/", #רמת גן גבעתיים סוף
    "https://www.facebook.com/groups/tlvrent/",
    "https://www.facebook.com/groups/35819517694/",
    "https://www.facebook.com/groups/295395253832427/",
    "https://www.facebook.com/groups/1749183625345821/",
    "https://www.facebook.com/groups/1664977427442936/",
    "https://www.facebook.com/groups/305724686290054/",
    "https://www.facebook.com/groups/785935868134249/",
    "https://www.facebook.com/groups/599822590152094/",
    "https://www.facebook.com/groups/676960712363338/",
    "https://www.facebook.com/groups/987764887999232/",
    "https://www.facebook.com/groups/785935868134249/",
    "https://www.facebook.com/groups/305724686290054/",
    "https://www.facebook.com/groups/2541381749432833/",
    "https://www.facebook.com/groups/1673941052823845/",
    "https://www.facebook.com/groups/apartments.tlv/",
    "https://www.facebook.com/groups/341195019300726/",
    "https://www.facebook.com/groups/291753646078748/",
    "https://www.facebook.com/groups/295395253832427/",
    "https://www.facebook.com/groups/tlvapartment/",
    "https://www.facebook.com/groups/458499457501175/",
    "https://www.facebook.com/groups/341195019300726/",
    "https://www.facebook.com/groups/2541381749432833/",
    "https://www.facebook.com/groups/333022240594651/",
    "https://www.facebook.com/groups/1749183625345821/",
    "https://www.facebook.com/groups/101875683484689/",
    "https://www.facebook.com/groups/291753646078748/",
    "https://www.facebook.com/groups/196649476429218/",
]

# ── Listing Filters (set to None to disable) ──
FILTERS = {
    "min_rooms": 2,
    "max_rooms": None,
    "min_sqm": 50,
    "max_sqm": None,
    "min_price": None,
    "max_price": 6000,
    "cities": ["גבעתיים" ,"תל אביב", "רמת גן"],
    # Map city -> list of allowed areas. None or missing city = allow all areas.
    "areas": {
        # "תל אביב": ["צפון ישן", "הצפון החדש", "לב העיר"],
        # "רמת גן": ["מרכז", "גבול גבעתיים"],
    },
    # Streets to exclude (case-insensitive Hebrew match)
    "excluded_streets": [
        # "דוגמה",
    ],
}

# ── "Is Catch" Filters — separate thresholds for catch detection ──
# Same keys as FILTERS. When is_catch is True, the listing must also
# pass these filters to be marked as a catch.
IS_CATCH_FILTERS = {
    "min_rooms": 2,
    "max_rooms": None,
    "min_sqm": 50,
    "max_sqm": None,
    "min_price": None,
    "max_price": 5000,
    "cities": ["תל אביב"],
    "areas": None,
}

# ── Scraping Intervals ──
CYCLE_INTERVAL_SECONDS = 20 * 60
GROUP_JITTER_BASE = 180  # seconds between groups
GROUP_JITTER_RANGE = 60  # +/- seconds

# ── Sheet Schema ──
SHEET_HEADERS = [
    "Timestamp", "City", "Area", "Street", "Price", "Rooms", "Size", "Phone", "Link", "Is Catch"
]
