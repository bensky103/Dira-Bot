import json
import logging
import random
import re
import time

import requests

logger = logging.getLogger(__name__)

# Yad2 city codes for rental search
YAD2_CITY_CODES = {
    "תל אביב": 5000,
    "רמת גן": 8600,
    "גבעתיים": 6300,
}

# Map Yad2 top-area IDs to Hebrew area names
TOP_AREA_NAMES = {
    1: "מרכז העיר",
    2: "צפון ישן",
    3: "צפון חדש",
    4: "לב העיר",
    5: "פלורנטין",
    6: "נווה צדק",
    7: "יפו",
    8: "רמת אביב",
}

API_URL = "https://gw.yad2.co.il/feed-search-legacy/realestate/rent"


class Yad2Scraper:
    """Yad2 rental listings scraper using their internal search API."""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
                "Gecko/20100101 Firefox/128.0"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "he,en-US;q=0.7,en;q=0.3",
            "Referer": "https://www.yad2.co.il/realestate/rent",
            "Origin": "https://www.yad2.co.il",
        })

    def scrape_city(self, city: str) -> list[dict]:
        """Scrape rental listings for a single city via Yad2 API."""
        city_code = YAD2_CITY_CODES.get(city)
        if not city_code:
            logger.warning("No Yad2 city code for %s", city)
            return []

        all_listings = []

        for page_num in range(1, 4):
            try:
                logger.info("Yad2 API: fetching %s page %d", city, page_num)

                resp = self._session.get(
                    API_URL,
                    params={
                        "city": city_code,
                        "propertyGroup": "apartments",
                        "page": page_num,
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

                feed_items = self._extract_feed_items(data)

                if not feed_items:
                    logger.info("Yad2 API: no items on %s page %d, stopping", city, page_num)
                    break

                parsed = [
                    p for item in feed_items
                    if (p := self._parse_item(item, city)) is not None
                ]

                all_listings.extend(parsed)
                logger.info("Yad2 API: got %d listings from %s page %d", len(parsed), city, page_num)

                # Check if there are more pages
                total_pages = data.get("data", {}).get("pagination", {}).get("last_page", 1)
                if page_num >= total_pages:
                    break

                if len(parsed) < 10:
                    break

                time.sleep(random.uniform(2, 5))

            except Exception as e:
                logger.error("Yad2 API error on %s page %d: %s", city, page_num, e)
                break

        logger.info("Yad2 API: total %d listings from %s", len(all_listings), city)
        return all_listings

    def _extract_feed_items(self, data: dict) -> list[dict]:
        """Extract listing items from the API response JSON."""
        feed = data.get("data", {}).get("feed", {}).get("feed_items", [])
        return [
            item for item in feed
            if isinstance(item, dict)
            and item.get("type") in ("ad", "item", None)
            and (item.get("id") or item.get("token") or item.get("link_token"))
        ]

    def _parse_item(self, item: dict, city: str) -> dict | None:
        """Parse a single API item into our standard listing format."""
        try:
            item_id = item.get("id") or item.get("token") or item.get("link_token")
            if not item_id:
                return None

            # Price
            price_raw = item.get("price", "")
            price = self._parse_number(str(price_raw))
            if not price:
                return None

            # Rooms
            rooms_raw = item.get("rooms")
            if not rooms_raw and isinstance(item.get("row_1"), list):
                for col in item["row_1"]:
                    if isinstance(col, dict) and col.get("key") == "rooms":
                        rooms_raw = col.get("value")
                        break
            rooms = self._parse_float(str(rooms_raw)) if rooms_raw else 0

            # Square meters
            sqm_raw = item.get("square_meters") or item.get("squareMeter")
            if not sqm_raw and isinstance(item.get("row_1"), list):
                for col in item["row_1"]:
                    if isinstance(col, dict) and col.get("key") == "square_meters":
                        sqm_raw = col.get("value")
                        break
            sqm = self._parse_number(str(sqm_raw)) if sqm_raw else 0

            # Address
            addr = item.get("address", {})
            if isinstance(addr, dict):
                street_obj = addr.get("street", {})
                street_name = street_obj.get("name", "") if isinstance(street_obj, dict) else str(street_obj)
                house_obj = addr.get("house", {})
                house_str = house_obj.get("number", "") if isinstance(house_obj, dict) else str(house_obj or "")
                neighborhood = addr.get("neighborhood", {})
                area = neighborhood.get("name", "") if isinstance(neighborhood, dict) else str(neighborhood or "")
                full_street = f"{street_name} {house_str}".strip()
            elif isinstance(addr, str):
                full_street = addr
                area = ""
            else:
                full_street = ""
                area = ""

            if not area:
                area = TOP_AREA_NAMES.get(item.get("top_area_id"), "")

            # Images
            images = []
            img_data = item.get("images") or item.get("media", {}).get("images", [])
            if isinstance(img_data, list):
                for img in img_data:
                    if isinstance(img, dict):
                        src = img.get("src") or img.get("url") or img.get("image_url", "")
                    elif isinstance(img, str):
                        src = img
                    else:
                        continue
                    if src:
                        images.append(src)

            listing_url = f"https://www.yad2.co.il/realestate/item/{item_id}"
            phone = item.get("phone", "") or ""

            return {
                "url": listing_url,
                "images": images,
                "city": city,
                "area": area or "לא ידוע",
                "street": full_street,
                "price_nis": price,
                "rooms": rooms,
                "sqm": sqm,
                "phone": str(phone),
                "is_catch": False,
            }

        except Exception as e:
            logger.debug("Failed to parse Yad2 item: %s", e)
            return None

    @staticmethod
    def _parse_number(s: str) -> int:
        if not s:
            return 0
        return int(re.sub(r'[^\d]', '', s) or 0)

    @staticmethod
    def _parse_float(s: str) -> float:
        if not s:
            return 0
        try:
            return float(re.sub(r'[^\d.]', '', s) or 0)
        except ValueError:
            return 0

    def close(self):
        self._session.close()
