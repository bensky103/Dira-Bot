import os
from dotenv import load_dotenv

load_dotenv()

# Persistent data directory: /data on Railway (volume), project root locally
DATA_DIR = "/data" if os.path.isdir("/data") else os.path.dirname(os.path.dirname(__file__))

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_IDS = [
    cid.strip() for cid in os.environ["TELEGRAM_CHAT_IDS"].split(",") if cid.strip()
]
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Dira-Bot")

# Facebook groups to scrape
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

# ── Listing Filters ──
# Only listings that pass ALL these filters get added to the sheet.
# Set any to None to disable that filter.
FILTERS = {
    "min_rooms": None,
    "max_rooms": None,
    "min_sqm": None,
    "max_sqm": None,
    "max_price": None,
    "min_price": None,
    "cities": ["תל אביב", "רמת גן"],  # None = accept all cities
}

# Scraping intervals
CYCLE_INTERVAL_SECONDS = 20 * 60  # 20 minutes
GROUP_JITTER_BASE = 180  # seconds between groups
GROUP_JITTER_RANGE = 60  # ± seconds

SHEET_HEADERS = [
    "Timestamp", "City", "Street", "Price", "Rooms", "Size", "Phone", "Link", "Is Catch"
]
