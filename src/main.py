import glob
import json
import logging
import os
import random
import time
from logging.handlers import RotatingFileHandler

from src.config import GROUPS, YAD2_CITIES, CYCLE_INTERVAL_SECONDS, GROUP_JITTER_BASE, GROUP_JITTER_RANGE, DATA_DIR
from src.scraper import Scraper
from src.yad2_scraper import Yad2Scraper
from src.parser import parse_post
from src.sheets import SheetClient
from src.notifier import send_catch_alert, send_session_expired_alert, send_batch_alert
from src.image_store import upload_images

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
    if not parsed.get("price_nis"):
        return "missing price"
    if not parsed.get("street"):
        return "missing street"
    if not parsed.get("rooms"):
        return "missing rooms"
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


def _process_yad2_listing(listing: dict, sheet: SheetClient, catch_config: dict | None) -> bool:
    """Process a single pre-parsed Yad2 listing. Returns True if added."""
    global _batch_counter

    reason = check_listing_valid(listing)
    if reason:
        logger.info("Yad2 skipped invalid: %s (%s)", listing.get("city", "?"), reason)
        return False

    if sheet.is_duplicate_listing(listing):
        logger.info(
            "Yad2 duplicate skipped: %s %s %s NIS",
            listing.get("city", "?"), listing.get("street", "?"), listing.get("price_nis", "?"),
        )
        return False

    images = upload_images(listing.get("images") or [])
    if not images:
        logger.info("Yad2 skipped (no images): %s %s", listing.get("city", "?"), listing.get("street", "?"))
        return False
    if not sheet.queue_listing(listing, listing["url"], images):
        return False
    _batch_counter += 1

    if check_catch_filters(listing, catch_config):
        send_catch_alert(listing, listing["url"])

    return True


def run_cycle(scraper: Scraper, yad2: Yad2Scraper, sheet: SheetClient):
    """Run one full scrape-parse-store cycle across all sources."""
    global _session_alert_sent, _batch_counter
    _cleanup_screenshots()
    surviving_links = sheet.cleanup_stale_rows()
    # Prune seen_urls to only keep URLs still in the sheet (prevents unbounded growth)
    before = len(_seen_urls)
    _seen_urls.intersection_update(surviving_links)
    pruned = before - len(_seen_urls)
    if pruned:
        logger.info("Pruned %d stale entries from seen_urls (%d remaining)", pruned, len(_seen_urls))
        _save_seen(_seen_urls)
    catch_config = sheet.load_catch_config()

    # ── Facebook Groups ──
    for i, group_url in enumerate(GROUPS):
        logger.info("Scraping group %d/%d: %s", i + 1, len(GROUPS), group_url)
        posts = scraper.scrape_group(group_url)

        # Session expiry: first group returns nothing → alert and skip cycle
        if i == 0 and len(posts) == 0:
            if not _session_alert_sent:
                logger.warning("First group returned 0 posts — session likely expired!")
                send_session_expired_alert()
                _session_alert_sent = True
            break
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

            images = upload_images(post.get("images") or [])
            if not images:
                skipped += 1
                continue
            if sheet.queue_listing(parsed, post["url"], images):
                added += 1
                _batch_counter += 1

                if parsed.get("is_catch") and check_catch_filters(parsed, catch_config):
                    send_catch_alert(parsed, post["url"])

        # Flush all queued rows for this group in one API call
        sheet.flush_pending()

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

    # ── Yad2 ──
    logger.info("Scraping Yad2...")
    for city in YAD2_CITIES:
        try:
            listings = yad2.scrape_city(city)
            new_listings = [
                l for l in listings
                if l["url"] not in _seen_urls and not sheet.link_exists(l["url"])
            ]
            logger.info("Yad2 %s: %d listings (%d new)", city, len(listings), len(new_listings))

            added = 0
            for listing in new_listings:
                _seen_urls.add(listing["url"])
                if _process_yad2_listing(listing, sheet, catch_config):
                    added += 1

            sheet.flush_pending()

            if _batch_counter >= BATCH_ALERT_THRESHOLD:
                send_batch_alert(_batch_counter)
                _batch_counter = 0

            logger.info("Yad2 %s: %d added", city, added)
            _save_seen(_seen_urls)

        except Exception as e:
            logger.error("Yad2 %s failed: %s", city, e)

        # Jitter between cities
        time.sleep(random.randint(5, 15))


def main():
    logger.info("Starting Dira-Bot")
    scraper = Scraper()
    scraper.start()
    yad2 = Yad2Scraper()
    yad2.start(scraper.playwright)
    sheet = SheetClient()

    try:
        while True:
            run_cycle(scraper, yad2, sheet)
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
        yad2.close()
        logging.shutdown()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
