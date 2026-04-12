import json
import logging
import random
import re
from playwright.sync_api import Browser, BrowserContext, Playwright

logger = logging.getLogger(__name__)

# Yad2 city codes for rental search
YAD2_CITY_CODES = {
    "תל אביב": 5000,
    "רמת גן": 8600,
    "גבעתיים": 6300,
}

# Map Yad2 top-area IDs to Hebrew area names (covers main neighborhoods)
# Listings that don't match get their neighborhood from the address field
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


class Yad2Scraper:
    """Yad2 rental listings scraper using a shared Playwright instance."""

    def __init__(self):
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    def start(self, playwright: Playwright):
        """Start using an existing Playwright instance (shared with Facebook scraper)."""
        self._browser = playwright.firefox.launch(headless=True)
        self._context = self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="he-IL",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
                "Gecko/20100101 Firefox/128.0"
            ),
        )

    def scrape_city(self, city: str) -> list[dict]:
        """Scrape rental listings for a single city.

        Returns list of dicts with pre-parsed fields:
        {url, images, city, area, street, price_nis, rooms, sqm, phone}
        """
        city_code = YAD2_CITY_CODES.get(city)
        if not city_code:
            logger.warning("No Yad2 city code for %s", city)
            return []

        all_listings = []
        page = self._context.new_page()

        try:
            # Scrape first few pages (Yad2 paginates with ?page=N)
            for page_num in range(1, 4):
                url = (
                    f"https://www.yad2.co.il/realestate/rent"
                    f"?city={city_code}&propertyGroup=apartments&page={page_num}"
                )
                logger.info("Yad2: fetching %s page %d", city, page_num)

                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(random.randint(3000, 5000))

                # Check for anti-bot page
                content = page.content()
                if "Are you for real" in content or "captcha" in content.lower():
                    logger.warning("Yad2 anti-bot detected on %s page %d, stopping", city, page_num)
                    break

                listings = self._extract_listings(page, city)

                if not listings:
                    logger.info("Yad2: no listings on %s page %d, stopping", city, page_num)
                    break

                all_listings.extend(listings)
                logger.info("Yad2: got %d listings from %s page %d", len(listings), city, page_num)

                # Don't fetch next page if this was a short page
                if len(listings) < 10:
                    break

                page.wait_for_timeout(random.randint(2000, 4000))

        except Exception as e:
            logger.error("Error scraping Yad2 %s: %s", city, e)
        finally:
            page.close()

        logger.info("Yad2: total %d listings from %s", len(all_listings), city)
        return all_listings

    def _extract_listings(self, page, city: str) -> list[dict]:
        """Extract listing data from the page via __NEXT_DATA__ or DOM fallback."""

        # Strategy 1: Try __NEXT_DATA__ JSON (cleanest)
        listings = self._extract_from_next_data(page, city)
        if listings:
            return listings

        # Strategy 2: DOM extraction fallback
        return self._extract_from_dom(page, city)

    def _extract_from_next_data(self, page, city: str) -> list[dict]:
        """Extract listings from Next.js __NEXT_DATA__ script tag."""
        try:
            next_data_raw = page.evaluate("""() => {
                const el = document.getElementById('__NEXT_DATA__');
                return el ? el.textContent : null;
            }""")

            if not next_data_raw:
                return []

            next_data = json.loads(next_data_raw)

            # Navigate the Next.js data structure to find listings
            # Common paths: props.pageProps.dehydratedState.queries[].state.data
            queries = (
                next_data.get("props", {})
                .get("pageProps", {})
                .get("dehydratedState", {})
                .get("queries", [])
            )

            feed_items = []
            for query in queries:
                data = query.get("state", {}).get("data", {})
                # Look for the feed data (usually has "data" or "feed" key with items)
                if isinstance(data, dict):
                    for key in ("data", "feed", "items", "pages"):
                        items = data.get(key)
                        if isinstance(items, list) and len(items) > 0:
                            # Could be paginated: [{items: [...]}] or flat: [item, item]
                            for item in items:
                                if isinstance(item, dict) and "items" in item:
                                    feed_items.extend(item["items"])
                                elif isinstance(item, dict) and self._looks_like_listing(item):
                                    feed_items.append(item)

            if not feed_items:
                return []

            logger.info("Yad2: found %d items in __NEXT_DATA__", len(feed_items))
            return [
                parsed
                for item in feed_items
                if (parsed := self._parse_next_data_item(item, city)) is not None
            ]

        except Exception as e:
            logger.debug("Yad2 __NEXT_DATA__ extraction failed: %s", e)
            return []

    @staticmethod
    def _looks_like_listing(item: dict) -> bool:
        """Heuristic: does this dict look like a Yad2 listing?"""
        return any(
            k in item
            for k in ("price", "rooms", "square_meters", "address", "id", "token")
        )

    def _parse_next_data_item(self, item: dict, city: str) -> dict | None:
        """Parse a single listing from __NEXT_DATA__ JSON into our format."""
        try:
            item_id = item.get("id") or item.get("token") or item.get("link_token")
            if not item_id:
                return None

            # Price
            price_raw = item.get("price") or item.get("price_text", "")
            price = self._parse_number(str(price_raw))
            if not price:
                return None

            # Rooms
            rooms = item.get("rooms") or item.get("row_1", [{}])[0].get("value") if isinstance(item.get("row_1"), list) else None
            rooms = self._parse_float(str(rooms)) if rooms else 0

            # Square meters
            sqm = item.get("square_meters") or item.get("squareMeter") or 0
            sqm = self._parse_number(str(sqm)) if sqm else 0

            # Address
            addr = item.get("address", {})
            if isinstance(addr, dict):
                street = addr.get("street", {})
                street_name = street.get("name", "") if isinstance(street, dict) else str(street)
                house_num = addr.get("house", {})
                house_str = house_num.get("number", "") if isinstance(house_num, dict) else str(house_num or "")
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

            # Build listing URL
            listing_url = f"https://www.yad2.co.il/realestate/item/{item_id}"

            # Phone (rarely in feed data, usually on detail page)
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

    def _extract_from_dom(self, page, city: str) -> list[dict]:
        """Fallback: extract listing data directly from rendered DOM."""
        try:
            raw = page.evaluate("""() => {
                const cards = document.querySelectorAll(
                    '[data-testid="feed-item"], [class*="feeditem"], [class*="feed_item"], [class*="listing"]'
                );
                if (cards.length === 0) return [];

                return Array.from(cards).map(card => {
                    const getText = (sel) => {
                        const el = card.querySelector(sel);
                        return el ? el.innerText.trim() : '';
                    };

                    const link = card.querySelector('a[href*="/realestate/item/"]');
                    const href = link ? link.getAttribute('href') : '';

                    const imgs = Array.from(card.querySelectorAll('img'));
                    const images = imgs
                        .map(i => i.getAttribute('src') || '')
                        .filter(s => s.includes('yad2') || s.includes('cloudinary') || s.startsWith('https://'));

                    // Yad2 uses various class patterns — grab all text and parse
                    const allText = card.innerText || '';

                    return {
                        href: href,
                        images: images,
                        text: allText
                    };
                });
            }""")

            if not raw:
                return []

            listings = []
            for item in raw:
                parsed = self._parse_dom_item(item, city)
                if parsed:
                    listings.append(parsed)

            return listings

        except Exception as e:
            logger.debug("Yad2 DOM extraction failed: %s", e)
            return []

    def _parse_dom_item(self, item: dict, city: str) -> dict | None:
        """Parse a DOM-extracted listing card."""
        href = item.get("href", "")
        if not href:
            return None

        if href.startswith("/"):
            href = "https://www.yad2.co.il" + href

        text = item.get("text", "")
        if len(text) < 10:
            return None

        # Extract structured data from text using regex
        price = self._parse_number(self._find_pattern(r'(\d[\d,]+)\s*₪', text))
        rooms = self._parse_float(self._find_pattern(r'([\d.]+)\s*חדר', text))
        sqm = self._parse_number(self._find_pattern(r'(\d+)\s*(?:מ"ר|מ״ר|מטר)', text))

        if not price:
            return None

        images = [img for img in item.get("images", []) if img and len(img) > 10]

        return {
            "url": href,
            "images": images,
            "city": city,
            "area": "לא ידוע",
            "street": "",
            "price_nis": price,
            "rooms": rooms or 0,
            "sqm": sqm or 0,
            "phone": "",
            "is_catch": False,
        }

    @staticmethod
    def _find_pattern(pattern: str, text: str) -> str:
        match = re.search(pattern, text)
        return match.group(1) if match else ""

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
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
