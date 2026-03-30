import asyncio
import json
import logging
import os
import random
import time
from logging.handlers import RotatingFileHandler

from src.config import GROUPS, CYCLE_INTERVAL_SECONDS, GROUP_JITTER_BASE, GROUP_JITTER_RANGE, FILTERS, DATA_DIR
from src.scraper import Scraper
from src.parser import parse_post
from src.sheets import SheetClient
from src.notifier import send_catch_alert, send_session_expired_alert

# ── Logging setup ──
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Console handler
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(log_format)

# File handler — rotates at 5MB, keeps 5 old files
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "dira-bot.log"),
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_format)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console)
root_logger.addHandler(file_handler)

# Suppress noisy third-party loggers
for noisy in ("asyncio", "httpx", "httpcore", "urllib3", "google", "gspread", "openai"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def check_filters(parsed: dict) -> str | None:
    """Return a reason string if the listing should be excluded, or None if it passes."""
    f = FILTERS
    price = parsed.get("price_nis", 0)
    rooms = parsed.get("rooms", 0)
    sqm = parsed.get("sqm", 0)
    city = parsed.get("city", "")

    if f["min_price"] and price and price < f["min_price"]:
        return f"price {price} < min {f['min_price']}"
    if f["max_price"] and price and price > f["max_price"]:
        return f"price {price} > max {f['max_price']}"
    if f["min_rooms"] and rooms and rooms < f["min_rooms"]:
        return f"rooms {rooms} < min {f['min_rooms']}"
    if f["max_rooms"] and rooms and rooms > f["max_rooms"]:
        return f"rooms {rooms} > max {f['max_rooms']}"
    if f["min_sqm"] and sqm and sqm < f["min_sqm"]:
        return f"sqm {sqm} < min {f['min_sqm']}"
    if f["max_sqm"] and sqm and sqm > f["max_sqm"]:
        return f"sqm {sqm} > max {f['max_sqm']}"
    if f["cities"] and city and city not in f["cities"]:
        return f"city '{city}' not in allowed list"

    return None


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


def run_cycle(scraper: Scraper, sheet: SheetClient):
    """Run one full scrape-parse-store cycle across all groups."""
    global _session_alert_sent

    for i, group_url in enumerate(GROUPS):
        logger.info("Scraping group %d/%d: %s", i + 1, len(GROUPS), group_url)
        posts = scraper.scrape_group(group_url)

        # Session expiry: first group returns nothing → alert and skip cycle
        if i == 0 and len(posts) == 0:
            if not _session_alert_sent:
                logger.warning("First group returned 0 posts — session likely expired!")
                asyncio.run(send_session_expired_alert())
                _session_alert_sent = True
            return
        elif len(posts) > 0:
            _session_alert_sent = False

        new_posts = [p for p in posts if p["url"] not in _seen_urls and not sheet.link_exists(p["url"])]
        logger.info("Got %d posts (%d new) from %s", len(posts), len(new_posts), group_url)

        added = 0
        skipped = 0
        filtered = 0
        for post in new_posts:
            _seen_urls.add(post["url"])

            parsed = parse_post(post["text"])
            if parsed is None:
                skipped += 1
                continue

            reason = check_filters(parsed)
            if reason:
                logger.info("Filtered out: %s (%s)", parsed.get("city", "?"), reason)
                filtered += 1
                continue

            sheet.append_listing(parsed, post["url"])
            added += 1

            if parsed.get("is_catch"):
                asyncio.run(send_catch_alert(parsed, post["url"]))

        logger.info(
            "Results: %d added, %d filtered, %d non-listings, %d already seen",
            added, filtered, skipped, len(posts) - len(new_posts),
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
