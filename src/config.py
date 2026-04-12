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
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

# ── Facebook Groups ──
GROUPS = [
    # ── תל אביב ──
    "https://www.facebook.com/groups/287564448778602/",
    "https://www.facebook.com/groups/196649476429218/",
    "https://www.facebook.com/groups/telavivrentals/",
    "https://www.facebook.com/groups/tlvrent/",
    "https://www.facebook.com/groups/tlvapartment/",
    "https://www.facebook.com/groups/apartments.tlv/",
    "https://www.facebook.com/groups/35819517694/",
    "https://www.facebook.com/groups/295395253832427/",
    "https://www.facebook.com/groups/1749183625345821/",
    "https://www.facebook.com/groups/1664977427442936/",
    "https://www.facebook.com/groups/305724686290054/",
    "https://www.facebook.com/groups/785935868134249/",
    "https://www.facebook.com/groups/599822590152094/",
    "https://www.facebook.com/groups/676960712363338/",
    "https://www.facebook.com/groups/987764887999232/",
    "https://www.facebook.com/groups/2541381749432833/",
    "https://www.facebook.com/groups/1673941052823845/",
    "https://www.facebook.com/groups/341195019300726/",
    "https://www.facebook.com/groups/291753646078748/",
    "https://www.facebook.com/groups/458499457501175/",
    "https://www.facebook.com/groups/333022240594651/",
    "https://www.facebook.com/groups/101875683484689/",
    # ── רמת גן / גבעתיים ──
    "https://www.facebook.com/groups/647901439404148/",
    "https://www.facebook.com/groups/253957624766723/",
    "https://www.facebook.com/groups/402682483445663/",
    "https://www.facebook.com/groups/1774413905909921/",
    "https://www.facebook.com/groups/1456553661265604",
    "https://www.facebook.com/groups/1870209196564360/",
    "https://www.facebook.com/groups/1424244737803677/",
]

# ── Yad2 Cities ──
YAD2_CITIES = ["תל אביב", "רמת גן", "גבעתיים"]

# ── Scraping Intervals ──
CYCLE_INTERVAL_SECONDS = 20 * 60
GROUP_JITTER_BASE = 180  # seconds between groups
GROUP_JITTER_RANGE = 60  # +/- seconds

# ── Sheet Schema ──
SHEET_HEADERS = [
    "Timestamp", "City", "Area", "Street", "Price", "Rooms", "Size", "Phone", "Link", "Is Catch", "Images"
]
