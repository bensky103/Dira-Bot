# Yad2 Fix, Favorites, Pin Overlap, Railway Cleanup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the broken Yad2 scraper by switching to direct API calls, add a favorites system with gold pins and deletion immunity, fix overlapping map pins, run Yad2 concurrently with Facebook scraping, and remove Railway deployment code.

**Architecture:** The Yad2 scraper is rewritten to use `requests` against Yad2's JSON API instead of Playwright. Favorites are stored as a new column in Google Sheets, read by the map API, toggled via a new endpoint, and rendered as gold markers. Pin overlap is resolved by a post-processing pass that detects collisions and offsets duplicates.

**Tech Stack:** Python (requests), Next.js (App Router), React-Leaflet, Google Sheets API, TypeScript

---

### Task 1: Delete Railway startup module

**Files:**
- Delete: `src/startup.py`

- [ ] **Step 1: Delete the file**

Delete `src/startup.py`. It's not imported anywhere in the codebase (confirmed via grep).

- [ ] **Step 2: Commit**

```bash
git add -u src/startup.py
git commit -m "chore: remove Railway startup module (no longer deployed there)"
```

---

### Task 2: Rewrite Yad2 scraper to use direct API

**Files:**
- Modify: `src/yad2_scraper.py` (full rewrite)

- [ ] **Step 1: Rewrite yad2_scraper.py**

Replace the entire file. The new scraper uses `requests.Session` to call Yad2's internal search API directly. Key changes:
- No Playwright imports or browser management
- `start()` method removed — no shared browser needed
- `close()` is a no-op (keeps interface compatible)
- Uses `requests.Session` with realistic browser headers
- Calls `https://gw.yad2.co.il/feed-search-legacy/realestate/rent` with query params
- Parses JSON response directly
- Same output format: `scrape_city(city) -> list[dict]`

```python
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
        # Filter to actual listings (type "ad" or items with a token/id)
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
```

- [ ] **Step 2: Commit**

```bash
git add src/yad2_scraper.py
git commit -m "feat: rewrite Yad2 scraper to use direct API instead of Playwright"
```

---

### Task 3: Run Yad2 concurrently with Facebook scraping in main.py

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: Update main.py**

Three changes:
1. Remove Playwright dependency from Yad2 — `yad2.start(scraper.playwright)` is no longer needed
2. Run Yad2 scraping in a background thread concurrently with Facebook groups
3. Process Yad2 results after both finish

At the top, add `import threading`.

In `main()`, change:
```python
yad2 = Yad2Scraper()
yad2.start(scraper.playwright)   # DELETE this line
```
to:
```python
yad2 = Yad2Scraper()
```

Replace the `run_cycle` function. The Yad2 section (lines 243-273) should run in a thread that collects results while Facebook groups are scraped. After Facebook finishes, join the thread and process Yad2 results.

```python
def _scrape_yad2_cities(yad2: Yad2Scraper) -> dict[str, list[dict]]:
    """Scrape all Yad2 cities. Runs in a background thread."""
    results = {}
    for city in YAD2_CITIES:
        try:
            results[city] = yad2.scrape_city(city)
        except Exception as e:
            logger.error("Yad2 %s failed: %s", city, e)
            results[city] = []
        time.sleep(random.randint(5, 15))
    return results


def run_cycle(scraper: Scraper, yad2: Yad2Scraper, sheet: SheetClient):
    """Run one full scrape-parse-store cycle across all sources."""
    global _session_alert_sent, _batch_counter
    _cleanup_screenshots()
    surviving_links = sheet.cleanup_stale_rows()
    before = len(_seen_urls)
    _seen_urls.intersection_update(surviving_links)
    pruned = before - len(_seen_urls)
    if pruned:
        logger.info("Pruned %d stale entries from seen_urls (%d remaining)", pruned, len(_seen_urls))
        _save_seen(_seen_urls)
    catch_config = sheet.load_catch_config()

    # ── Start Yad2 in background thread ──
    yad2_results: dict[str, list[dict]] = {}

    def yad2_worker():
        nonlocal yad2_results
        yad2_results = _scrape_yad2_cities(yad2)

    yad2_thread = threading.Thread(target=yad2_worker, name="yad2-scraper")
    yad2_thread.start()
    logger.info("Yad2 scraping started in background thread")

    # ── Facebook Groups (runs concurrently with Yad2) ──
    for i, group_url in enumerate(GROUPS):
        logger.info("Scraping group %d/%d: %s", i + 1, len(GROUPS), group_url)
        posts = scraper.scrape_group(group_url)

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

        sheet.flush_pending()

        if _batch_counter >= BATCH_ALERT_THRESHOLD:
            send_batch_alert(_batch_counter)
            _batch_counter = 0

        logger.info(
            "Results: %d added, %d filtered, %d duplicates, %d non-listings, %d already seen",
            added, filtered, duplicates, skipped, len(posts) - len(new_posts),
        )
        _save_seen(_seen_urls)

        if i < len(GROUPS) - 1:
            wait = GROUP_JITTER_BASE + random.randint(
                -GROUP_JITTER_RANGE, GROUP_JITTER_RANGE
            )
            logger.info("Waiting %d seconds before next group...", wait)
            time.sleep(wait)

    # ── Wait for Yad2 thread and process results ──
    yad2_thread.join()
    logger.info("Yad2 scraping complete, processing results...")

    for city, listings in yad2_results.items():
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
```

- [ ] **Step 2: Verify the bot starts correctly**

```bash
cd "C:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
python -c "from src.yad2_scraper import Yad2Scraper; y = Yad2Scraper(); print('OK')"
```

Expected: `OK` (no Playwright needed)

- [ ] **Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat: run Yad2 scraping concurrently with Facebook in background thread"
```

---

### Task 4: Add Favorite column to sheet schema and protect favorites from deletion

**Files:**
- Modify: `src/config.py`
- Modify: `src/sheets.py`

- [ ] **Step 1: Add Favorite to SHEET_HEADERS in config.py**

In `src/config.py`, change the `SHEET_HEADERS` list to add `"Favorite"` at the end:

```python
SHEET_HEADERS = [
    "Timestamp", "City", "Area", "Street", "Price", "Rooms", "Size", "Phone", "Link", "Is Catch", "Images", "Favorite"
]
```

- [ ] **Step 2: Update sheets.py — build_row, cleanup, and backfill**

In `src/sheets.py`:

**a) `_build_row()`** — append `"False"` for the Favorite column:

Change the return list in `_build_row()` to add `"False"` at the end:

```python
def _build_row(self, parsed: dict, link: str, images: list[str] | None = None) -> list:
    """Build a sheet row from parsed data."""
    return [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        parsed.get("city", ""),
        parsed.get("area", ""),
        parsed.get("street", ""),
        parsed.get("price_nis", ""),
        parsed.get("rooms", ""),
        parsed.get("sqm", ""),
        parsed.get("phone", ""),
        link,
        str(parsed.get("is_catch", False)),
        "|".join(images) if images else "",
        "False",
    ]
```

**b) `cleanup_stale_rows()`** — skip rows where Favorite is "True":

In the loop that finds stale indices, add a check for the Favorite column. The Favorite column is at index 11 (0-indexed). Change the stale detection loop:

```python
stale_indices = []
fav_col = SHEET_HEADERS.index("Favorite")
for i, row in enumerate(all_rows[1:], start=2):
    try:
        # Skip favorited rows — they are immune to cleanup
        if len(row) > fav_col and row[fav_col].strip().lower() == "true":
            continue
        ts = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
        if ts < cutoff:
            stale_indices.append(i)
    except (ValueError, IndexError):
        continue
```

**c) `__init__()`** — backfill existing rows with "False" if Favorite column is missing:

Add a `_backfill_favorites()` call after `_ensure_headers()`:

```python
def __init__(self):
    sa_path = os.path.join(DATA_DIR, "service_account.json")
    creds = Credentials.from_service_account_file(sa_path, scopes=SCOPES)
    gc = gspread.authorize(creds)
    self._workbook = gc.open(GOOGLE_SHEET_NAME)
    self._sheet = self._workbook.sheet1
    self._ensure_headers()
    self._backfill_favorites()
    # Cache links in memory to avoid repeated API calls
    self._known_links: set[str] = set(self._sheet.col_values(
        SHEET_HEADERS.index("Link") + 1
    ))
    self._known_composites: set[tuple] = self._load_composite_keys()
    self._pending_rows: list[list] = []
```

Add the backfill method:

```python
def _backfill_favorites(self):
    """Fill empty Favorite column cells with 'False' for existing rows."""
    fav_col = SHEET_HEADERS.index("Favorite") + 1  # 1-indexed for gspread
    col_values = self._sheet.col_values(fav_col)
    # col_values may be shorter than total rows if column was just added
    total_rows = self._sheet.row_count
    all_rows = self._sheet.get_all_values()
    updates = []
    for i, row in enumerate(all_rows[1:], start=2):  # skip header
        if len(row) < fav_col or not row[fav_col - 1].strip():
            updates.append({"range": f"{chr(64 + fav_col)}{i}", "values": [["False"]]})
    if updates:
        self._sheet.batch_update(updates)
        logger.info("Backfilled %d rows with Favorite=False", len(updates))
```

- [ ] **Step 3: Commit**

```bash
git add src/config.py src/sheets.py
git commit -m "feat: add Favorite column to sheet schema, protect favorites from stale cleanup"
```

---

### Task 5: Add favorite field to map backend

**Files:**
- Modify: `map/src/types/apartment.ts`
- Modify: `map/src/lib/sheets.ts`
- Modify: `map/src/app/api/apartments/route.ts`

- [ ] **Step 1: Update the Apartment type**

In `map/src/types/apartment.ts`, add `isFavorite`:

```typescript
export interface Apartment {
  timestamp: string;
  city: string;
  area: string;
  street: string;
  price: number;
  rooms: number;
  size: number;
  phone: string;
  link: string;
  isCatch: boolean;
  isFavorite: boolean;
  lat: number;
  lng: number;
  images: string[];
}
```

- [ ] **Step 2: Read Favorite column from sheets**

In `map/src/lib/sheets.ts`, add `favorite` to the `SheetRow` interface and the `fetchApartments()` mapper:

Add to `SheetRow`:
```typescript
interface SheetRow {
  timestamp: string;
  city: string;
  area: string;
  street: string;
  price: string;
  rooms: string;
  size: string;
  phone: string;
  link: string;
  isCatch: string;
  images: string;
  favorite: string;
}
```

In `fetchApartments()`, add the mapping:
```typescript
favorite: row.get("Favorite") || "False",
```

- [ ] **Step 3: Pass isFavorite through in the apartments API route**

In `map/src/app/api/apartments/route.ts`, in the `loadApartments()` function where the `Apartment` object is built, add:

```typescript
isFavorite: row.favorite === "True" || row.favorite === "true",
```

This goes in the `rows.map()` return object, after the `isCatch` line.

- [ ] **Step 4: Commit**

```bash
git add map/src/types/apartment.ts map/src/lib/sheets.ts map/src/app/api/apartments/route.ts
git commit -m "feat: pipe Favorite column through map API as isFavorite"
```

---

### Task 6: Create favorite toggle API endpoint

**Files:**
- Create: `map/src/app/api/apartments/favorite/route.ts`

- [ ] **Step 1: Create the endpoint**

Create `map/src/app/api/apartments/favorite/route.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server";
import { GoogleSpreadsheet } from "google-spreadsheet";
import { JWT } from "google-auth-library";

export async function POST(request: NextRequest) {
  try {
    const { link, favorite } = await request.json();
    if (!link || typeof favorite !== "boolean") {
      return NextResponse.json(
        { error: "Missing link or favorite boolean" },
        { status: 400 }
      );
    }

    const creds = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_JSON || "{}");
    const jwt = new JWT({
      email: creds.client_email,
      key: creds.private_key,
      scopes: ["https://www.googleapis.com/auth/spreadsheets"],
    });

    const doc = new GoogleSpreadsheet(process.env.GOOGLE_SHEET_ID!, jwt);
    await doc.loadInfo();

    const sheetName = process.env.GOOGLE_SHEET_NAME || "Dira-Bot";
    const sheet = doc.sheetsByTitle[sheetName] ?? doc.sheetsByIndex[0];
    const rows = await sheet.getRows();

    const row = rows.find((r) => r.get("Link") === link);
    if (!row) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    row.set("Favorite", favorite ? "True" : "False");
    await row.save();

    return NextResponse.json({ ok: true, favorite });
  } catch (error) {
    console.error("Favorite toggle error:", error);
    return NextResponse.json(
      { error: "Failed to toggle favorite" },
      { status: 500 }
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add map/src/app/api/apartments/favorite/route.ts
git commit -m "feat: add POST /api/apartments/favorite endpoint"
```

---

### Task 7: Add gold marker and favorite button to map frontend

**Files:**
- Modify: `map/src/components/MapView.tsx`
- Modify: `map/src/components/ApartmentPopup.tsx`
- Modify: `map/src/app/globals.css`

- [ ] **Step 1: Add gold marker icon in MapView.tsx**

Add a `favoriteIcon` after the existing `catchIcon` definition:

```typescript
const favoriteIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
  className: "favorite-marker",
});
```

Update the `MapViewProps` interface and component to accept `onFavorite`:

```typescript
interface MapViewProps {
  apartments: Apartment[];
  onDelete?: (link: string) => void;
  onFavorite?: (link: string, favorite: boolean) => void;
}

export default function MapView({ apartments, onDelete, onFavorite }: MapViewProps) {
```

Update the icon selection in the Marker to use priority: favorite > catch > default:

```typescript
icon={apt.isFavorite ? favoriteIcon : apt.isCatch ? catchIcon : defaultIcon}
```

Pass `onFavorite` to `ApartmentPopup`:

```typescript
<ApartmentPopup apartment={apt} onDelete={onDelete} onFavorite={onFavorite} />
```

- [ ] **Step 2: Add star button in ApartmentPopup.tsx**

Update the props interface:

```typescript
interface ApartmentPopupProps {
  apartment: Apartment;
  onDelete?: (link: string) => void;
  onFavorite?: (link: string, favorite: boolean) => void;
}
```

Update the component signature:

```typescript
export default function ApartmentPopup({ apartment, onDelete, onFavorite }: ApartmentPopupProps) {
```

Add a `toggling` state:

```typescript
const [toggling, setToggling] = useState(false);
```

Add a handler:

```typescript
const handleFavorite = async () => {
  setToggling(true);
  onFavorite?.(apartment.link, !apartment.isFavorite);
  setToggling(false);
};
```

Add the star button in the popup-header div, between the area-name span and the catch badge. Replace the existing `popup-header` div:

```tsx
<div className="popup-header">
  <span className="area-name">{apartment.area}</span>
  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
    {apartment.isCatch && <span className="catch-badge">🔥 CATCH</span>}
    <button
      className={`favorite-btn ${apartment.isFavorite ? "active" : ""}`}
      onClick={handleFavorite}
      disabled={toggling}
      title={apartment.isFavorite ? "Remove from favorites" : "Add to favorites"}
    >
      ★
    </button>
  </div>
</div>
```

- [ ] **Step 3: Add CSS for favorite marker and button**

Add to `map/src/app/globals.css`:

```css
/* ── Favorite Marker ── */
.favorite-marker {
  filter: hue-rotate(200deg) saturate(5) brightness(1.2);
}

/* ── Favorite Button ── */
.favorite-btn {
  background: none;
  border: 1px solid #334155;
  border-radius: 4px;
  color: #94a3b8;
  font-size: 16px;
  cursor: pointer;
  padding: 2px 6px;
  line-height: 1;
  transition: all 0.15s;
  flex-shrink: 0;
}

.favorite-btn:hover {
  color: #fbbf24;
  border-color: #fbbf24;
}

.favorite-btn.active {
  color: #fbbf24;
  border-color: #fbbf24;
  background: rgba(251, 191, 36, 0.1);
}

.favorite-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

- [ ] **Step 4: Commit**

```bash
git add map/src/components/MapView.tsx map/src/components/ApartmentPopup.tsx map/src/app/globals.css
git commit -m "feat: gold markers for favorites with star toggle button in popups"
```

---

### Task 8: Wire favorite toggle and filter into page.tsx and Sidebar

**Files:**
- Modify: `map/src/app/page.tsx`
- Modify: `map/src/components/Sidebar.tsx`
- Modify: `map/src/components/MapViewDynamic.tsx`

- [ ] **Step 1: Add favoritesOnly filter to Sidebar types and UI**

In `map/src/components/Sidebar.tsx`:

Add `favoritesOnly: boolean` to the `Filters` interface:

```typescript
export interface Filters {
  timeRange: string;
  minPrice: number;
  maxPrice: number;
  minSqm: number;
  maxSqm: number;
  rooms: number[];
  catchesOnly: boolean;
  favoritesOnly: boolean;
  cities: string[];
  catchCriteria: CatchCriteria;
}
```

Add `favoriteCount: number` to `SidebarProps`:

```typescript
interface SidebarProps {
  totalCount: number;
  catchCount: number;
  favoriteCount: number;
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  onRefresh: () => void;
  lastUpdated: Date | null;
}
```

Update the component signature to destructure `favoriteCount`:

```typescript
export default function Sidebar({
  totalCount,
  catchCount,
  favoriteCount,
  filters,
  onFiltersChange,
  onRefresh,
  lastUpdated,
}: SidebarProps) {
```

Add a toggle callback:

```typescript
const toggleFavoritesOnly = useCallback(
  () =>
    onFiltersChange({ ...filters, favoritesOnly: !filters.favoritesOnly }),
  [filters, onFiltersChange]
);
```

Add a stat card for favorites in the stats div, after the Catches stat card:

```tsx
<div className="stat-card">
  <div className="value" style={{ color: "#fbbf24" }}>
    {favoriteCount}
  </div>
  <div className="label">Favorites</div>
</div>
```

Add a favorites toggle row after the catches toggle row:

```tsx
<div className="toggle-row">
  <span style={{ fontSize: 13 }}>★ Favorites only</span>
  <div
    className={`toggle-switch ${filters.favoritesOnly ? "on" : ""}`}
    onClick={toggleFavoritesOnly}
  >
    <div className="toggle-knob" />
  </div>
</div>
```

- [ ] **Step 2: Update page.tsx — favorite handler, filter, and pass to children**

In `map/src/app/page.tsx`:

Add `favoritesOnly: false` to `DEFAULT_FILTERS`:

```typescript
const DEFAULT_FILTERS: Filters = {
  timeRange: "7d",
  minPrice: 0,
  maxPrice: 0,
  minSqm: 0,
  maxSqm: 0,
  rooms: [],
  catchesOnly: false,
  favoritesOnly: false,
  cities: ["תל אביב", "רמת גן", "גבעתיים"],
  catchCriteria: {
    maxPrice: 5000,
    minRooms: 2,
    minSqm: 50,
    cities: ["תל אביב"],
  },
};
```

Add a `handleFavorite` callback after `handleDelete`:

```typescript
const handleFavorite = useCallback(async (link: string, favorite: boolean) => {
  // Optimistic update
  setApartments((prev) =>
    prev.map((apt) =>
      apt.link === link ? { ...apt, isFavorite: favorite } : apt
    )
  );
  try {
    const res = await fetch("/api/apartments/favorite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ link, favorite }),
    });
    if (!res.ok) throw new Error("Favorite toggle failed");
  } catch (err) {
    console.error("Failed to toggle favorite:", err);
    // Revert on error
    setApartments((prev) =>
      prev.map((apt) =>
        apt.link === link ? { ...apt, isFavorite: !favorite } : apt
      )
    );
  }
}, []);
```

In the `filtered` useMemo, add the favoritesOnly filter after the catchesOnly check:

```typescript
// Favorites only
if (filters.favoritesOnly && !apt.isFavorite) return false;
```

Add the favorite count:

```typescript
const favoriteCount = filtered.filter((a) => a.isFavorite).length;
```

Pass `favoriteCount` and `onFavorite` to children. Update the `Sidebar` usage:

```tsx
<Sidebar
  totalCount={filtered.length}
  catchCount={catchCount}
  favoriteCount={favoriteCount}
  filters={filters}
  onFiltersChange={handleFiltersChange}
  onRefresh={() => fetchData(true)}
  lastUpdated={lastUpdated}
/>
```

Update the `MapViewDynamic` usage to pass `onFavorite`:

```tsx
<MapViewDynamic apartments={filtered} onDelete={handleDelete} onFavorite={handleFavorite} />
```

- [ ] **Step 3: Update MapViewDynamic to pass onFavorite**

In `map/src/components/MapViewDynamic.tsx`, add `onFavorite` to the props that get forwarded. Read the file first to see the exact dynamic import pattern, then add `onFavorite` to the props interface and forwarding.

The file uses `next/dynamic` to wrap `MapView`. The props type must include `onFavorite`. Since it imports from MapView, just make sure it forwards all props.

- [ ] **Step 4: Commit**

```bash
git add map/src/app/page.tsx map/src/components/Sidebar.tsx map/src/components/MapViewDynamic.tsx
git commit -m "feat: favorites filter toggle in sidebar with optimistic UI updates"
```

---

### Task 9: Fix overlapping pins with collision detection

**Files:**
- Modify: `map/src/app/api/apartments/route.ts`

- [ ] **Step 1: Add collision detection after coordinate resolution**

In `map/src/app/api/apartments/route.ts`, add a `spreadOverlappingPins` function and call it after `loadApartments()` builds the apartments array (before the `return` statement that filters out price=0).

Add this function above `loadApartments()`:

```typescript
function spreadOverlappingPins(apartments: Apartment[]): void {
  // Group by rounded coordinates (5 decimal places ≈ ~1m precision)
  const groups = new Map<string, number[]>();
  for (let i = 0; i < apartments.length; i++) {
    const key = `${apartments[i].lat.toFixed(5)},${apartments[i].lng.toFixed(5)}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(i);
  }

  // Offset overlapping pins in a circle pattern
  const OFFSET = 0.0002; // ~20m at Tel Aviv latitude
  for (const indices of groups.values()) {
    if (indices.length <= 1) continue;
    const count = indices.length;
    for (let j = 0; j < count; j++) {
      const angle = (2 * Math.PI * j) / count;
      apartments[indices[j]].lat += OFFSET * Math.cos(angle);
      apartments[indices[j]].lng += OFFSET * Math.sin(angle);
    }
  }
}
```

Call it in `loadApartments()`, right before the filter/return line:

```typescript
spreadOverlappingPins(apartments);

return apartments.filter((a) => a.price > 0 && a.lat !== 0);
```

Change `const apartments` to `let apartments` since we need to reassign after `Promise.all`:

Actually we don't reassign — `spreadOverlappingPins` mutates in place. But the `apartments` variable is declared with `const` and built from `Promise.all`. Since we're mutating elements (not the array reference), `const` is fine.

- [ ] **Step 2: Commit**

```bash
git add map/src/app/api/apartments/route.ts
git commit -m "fix: spread overlapping map pins using circular offset pattern"
```

---

### Task 10: Manual testing

- [ ] **Step 1: Test Yad2 scraper**

Run a quick test of the Yad2 scraper standalone:

```bash
cd "C:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
python -c "
from src.yad2_scraper import Yad2Scraper
y = Yad2Scraper()
listings = y.scrape_city('תל אביב')
print(f'Got {len(listings)} listings')
if listings:
    print(listings[0])
y.close()
"
```

Expected: Non-zero listings with proper fields (url, price_nis, city, etc.)

- [ ] **Step 2: Test the map UI**

```bash
cd "C:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot/map"
npm run dev
```

Open `http://localhost:3000` and verify:
1. Pins don't overlap (zoom in on a neighborhood center)
2. Favorites stat card shows in sidebar
3. Star button appears in popup — clicking it turns the pin gold
4. "Favorites only" toggle works
5. Favorited apartments persist after refresh

- [ ] **Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address issues found during manual testing"
```
