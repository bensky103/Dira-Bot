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

# ── Facebook Groups ──
GROUPS = [
    "https://www.facebook.com/groups/785935868134249/",
    "https://www.facebook.com/groups/305724686290054/",
    "https://www.facebook.com/groups/2541381749432833/",
    "https://www.facebook.com/groups/341195019300726/",
    "https://www.facebook.com/groups/295395253832427/",
    "https://www.facebook.com/groups/1749183625345821/",
    "https://www.facebook.com/groups/291753646078748/",
    "https://www.facebook.com/groups/196649476429218/",
]

# ── Listing Filters (set to None to disable) ──
FILTERS = {
    "min_rooms": 1,
    "max_rooms": 3,
    "min_sqm": 40,
    "max_sqm": None,
    "min_price": None,
    "max_price": 6000,
    "cities": ["תל אביב", "רמת גן"],
}

# ── Scraping Intervals ──
CYCLE_INTERVAL_SECONDS = 20 * 60
GROUP_JITTER_BASE = 180  # seconds between groups
GROUP_JITTER_RANGE = 60  # +/- seconds

# ── Sheet Schema ──
SHEET_HEADERS = [
    "Timestamp", "City", "Street", "Price", "Rooms", "Size", "Phone", "Link", "Is Catch"
]
