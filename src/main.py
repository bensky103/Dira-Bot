import glob
import json
import logging
import os
import random
import time
from logging.handlers import RotatingFileHandler

from src.config import GROUPS, CYCLE_INTERVAL_SECONDS, GROUP_JITTER_BASE, GROUP_JITTER_RANGE, DATA_DIR
from src.scraper import Scraper
from src.parser import parse_post
from src.sheets import SheetClient
from src.notifier import send_catch_alert, send_session_expired_alert, send_batch_alert

# ── Logging setup ──
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Console handler
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(log_format)

# File handler — rotates at ~10K lines (~1MB), keeps 3 old files
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "dira-bot.log"),
    maxBytes=1 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8",
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(log_format)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console)
root_logger.addHandler(file_handler)

# Suppress noisy third-party loggers
for noisy in ("asyncio", "httpx", "httpcore", "urllib3", "google", "gspread", "openai"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def check_listing_valid(parsed: dict) -> str | None:
    """Return a reason string if the listing is invalid, or None if it should be saved."""
    if not parsed.get("city"):
        return "missing city"
    return None


def check_catch_filters(parsed: dict, catch_config: dict | None) -> bool:
    """Return True if the listing matches catch criteria from the sheet Config tab."""
    if not catch_config:
        return False

    price = parsed.get("price_nis", 0)
    rooms = parsed.get("rooms", 0)
    sqm = parsed.get("sqm", 0)
    city = parsed.get("city", "")

    if catch_config.get("max_price") and price and price > catch_config["max_price"]:
        return False
    if catch_config.get("min_rooms") and rooms and rooms < catch_config["min_rooms"]:
        return False
    if catch_config.get("min_sqm") and sqm and sqm < catch_config["min_sqm"]:
        return False
    if catch_config.get("cities") and city and city not in catch_config["cities"]:
        return False

    return True


# Persist seen URLs to disk so restarts don't re-process old posts
SEEN_FILE = os.path.join(DATA_DIR, "seen_urls.json")


def _load_seen() -> set[str]:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def _save_seen(seen: set[str]):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f)


_seen_urls = _load_seen()


_session_alert_sent = False
_batch_counter = 0  # Tracks listings added since last batch alert
BATCH_ALERT_THRESHOLD = 100


def _cleanup_screenshots():
    """Delete all .png files from the logs directory."""
    for png in glob.glob(os.path.join(LOG_DIR, "*.png")):
        try:
            os.remove(png)
        except OSError:
            pass


def run_cycle(scraper: Scraper, sheet: SheetClient):
    """Run one full scrape-parse-store cycle across all groups."""
    global _session_alert_sent, _batch_counter
    _cleanup_screenshots()
    sheet.cleanup_stale_rows()
    catch_config = sheet.load_catch_config()

    for i, group_url in enumerate(GROUPS):
        logger.info("Scraping group %d/%d: %s", i + 1, len(GROUPS), group_url)
        posts = scraper.scrape_group(group_url)

        # Session expiry: first group returns nothing → alert and skip cycle
        if i == 0 and len(posts) == 0:
            if not _session_alert_sent:
                logger.warning("First group returned 0 posts — session likely expired!")
                send_session_expired_alert()
                _session_alert_sent = True
            return
        elif len(posts) > 0:
            _session_alert_sent = False

        new_posts = [
            p for p in posts
            if not p["url"].startswith("__no_link__")
            and p["url"] not in _seen_urls
            and not sheet.link_exists(p["url"])
        ]
        logger.info("Got %d posts (%d new) from %s", len(posts), len(new_posts), group_url)

        added = 0
        skipped = 0
        filtered = 0
        duplicates = 0
        for post in new_posts:
            _seen_urls.add(post["url"])

            parsed = parse_post(post["text"])
            if parsed is None:
                skipped += 1
                continue

            reason = check_listing_valid(parsed)
            if reason:
                logger.info("Skipped invalid: %s (%s)", parsed.get("city", "?"), reason)
                filtered += 1
                continue

            if sheet.is_duplicate_listing(parsed):
                logger.info(
                    "Duplicate listing skipped: %s %s %s NIS",
                    parsed.get("city", "?"), parsed.get("street", "?"), parsed.get("price_nis", "?"),
                )
                duplicates += 1
                continue

            sheet.append_listing(parsed, post["url"])
            added += 1
            _batch_counter += 1

            if parsed.get("is_catch") and check_catch_filters(parsed, catch_config):
                send_catch_alert(parsed, post["url"])

        # Send batch alert every 5 new listings
        if _batch_counter >= BATCH_ALERT_THRESHOLD:
            send_batch_alert(_batch_counter)
            _batch_counter = 0

        logger.info(
            "Results: %d added, %d filtered, %d duplicates, %d non-listings, %d already seen",
            added, filtered, duplicates, skipped, len(posts) - len(new_posts),
        )
        _save_seen(_seen_urls)

        # Jitter between groups (skip after last group)
        if i < len(GROUPS) - 1:
            wait = GROUP_JITTER_BASE + random.randint(
                -GROUP_JITTER_RANGE, GROUP_JITTER_RANGE
            )
            logger.info("Waiting %d seconds before next group...", wait)
            time.sleep(wait)


def main():
    logger.info("Starting Dira-Bot")
    scraper = Scraper()
    scraper.start()
    sheet = SheetClient()

    try:
        while True:
            run_cycle(scraper, sheet)
            logger.info(
                "Cycle complete. Sleeping %d minutes...",
                CYCLE_INTERVAL_SECONDS // 60,
            )
            time.sleep(CYCLE_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Shutting down...")
        scraper.close()
        logging.shutdown()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
