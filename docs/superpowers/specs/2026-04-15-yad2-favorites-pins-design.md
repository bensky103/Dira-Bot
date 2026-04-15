# Yad2 Scraper Fix, Favorites, Pin Overlap, Railway Cleanup

**Date:** 2026-04-15

## 1. Yad2 Scraper: Direct API

### Problem
Playwright headless Firefox is detected by Yad2's anti-bot on every request — 0 listings retrieved across all cycles.

### Solution
Replace browser-based scraping with direct HTTP calls to Yad2's internal search API.

**Endpoint:** `https://gw.yad2.co.il/feed-search-legacy/realestate/rent`
**Params:** `city=<code>&propertyGroup=apartments&page=<n>`

**Changes to `src/yad2_scraper.py`:**
- Remove all Playwright dependencies (Browser, BrowserContext, Page)
- Remove `start(playwright)` — no shared browser needed
- Use `requests.Session` with realistic headers (User-Agent, Accept, Referer)
- Parse JSON response directly (no `__NEXT_DATA__`, no DOM extraction)
- Keep same `scrape_city(city) -> list[dict]` interface
- Keep same output dict format: `{url, images, city, area, street, price_nis, rooms, sqm, phone, is_catch}`
- Retain random delays between requests (2-5s between pages, 5-15s between cities)

**Changes to `src/main.py`:**
- Run Yad2 scraping concurrently with Facebook scraping using `threading.Thread`
- `Yad2Scraper` no longer needs `start(playwright)` — just instantiate and call
- Yad2 thread collects results, main thread processes them after Facebook is done

## 2. Overlapping Pins: Collision Detection

### Problem
Multiple apartments at the same address get identical geocoded coordinates. The `hashOffset` only applies to neighborhood-level fallback, not geocoded results.

### Solution
Post-processing pass in `loadApartments()` (map API route) after all coordinates are resolved.

**Algorithm:**
1. Group apartments by rounded `(lat, lng)` (to ~1m precision, 5 decimal places)
2. For groups with >1 apartment, offset each by a small amount in a circle pattern
3. Offset radius: ~0.0002° (~20m) — enough to visually separate without moving pins far

**File:** `map/src/app/api/apartments/route.ts`

## 3. Favorites System

### Data Layer (Google Sheet)
- Add `"Favorite"` to `SHEET_HEADERS` in `src/config.py` (column 12)
- `sheets.py` `_build_row()` appends `"False"` for new listings
- `sheets.py` `cleanup_stale_rows()` skips rows where Favorite column is `"True"`
- Backfill: on `SheetClient.__init__`, if existing rows lack column 12, fill with `"False"`

### Map Backend
- `map/src/lib/sheets.ts`: Read `Favorite` column from sheet
- `map/src/types/apartment.ts`: Add `isFavorite: boolean` to interface
- `map/src/app/api/apartments/route.ts`: Pass `isFavorite` through
- New API route `map/src/app/api/apartments/favorite/route.ts`:
  - POST `{link, favorite: boolean}` — sets Favorite column to "True"/"False"

### Map Frontend
- **Gold marker:** New `favoriteIcon` with gold hue-rotate CSS class
- **Icon priority:** favorite > catch > default
- **Popup:** Star/unstar button in `ApartmentPopup.tsx`
- **Sidebar:** "Favorites only" toggle filter + favorites count display
- **Filtering:** Favorited apartments visible in all time ranges (they persist)

## 4. Railway Cleanup
- Delete `src/startup.py`
- Remove any imports of `startup` / `ensure_secrets` from codebase
