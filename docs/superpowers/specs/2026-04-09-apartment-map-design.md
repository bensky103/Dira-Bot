# Dira-Bot Apartment Map — Design Spec

## Overview

An interactive map visualization for Dira-Bot apartment listings, deployed on Vercel, pulling data from the existing Google Sheet. The map shows apartment clusters by neighborhood with drill-down to individual listings, filtering by time, price, rooms, and catch status.

## Architecture

### Stack

- **Framework:** Next.js (App Router)
- **Hosting:** Vercel (free tier)
- **Map:** Leaflet + OpenStreetMap Carto tiles (free, no API key)
- **Data source:** Google Sheets via `google-spreadsheet` npm package + Google service account
- **Project location:** `map/` directory inside the Dira-Bot repo (separate Next.js project)

### Data Flow

```
Google Sheet ──→ /api/apartments (Next.js API route) ──→ Browser ──→ Leaflet Map
                      │
                 5-min server cache
```

### API Route: `/api/apartments`

Single endpoint that:

1. Authenticates with Google Sheets using the service account JSON (stored as Vercel env var)
2. Fetches all rows from the sheet
3. Returns JSON array of apartments:
   ```json
   [
     {
       "timestamp": "2026-04-09T14:30:00",
       "city": "תל אביב",
       "area": "צפון ישן",
       "street": "דיזנגוף 99",
       "price": 4200,
       "rooms": 3,
       "size": 65,
       "phone": "050-1234567",
       "link": "https://facebook.com/...",
       "isCatch": true,
       "lat": 32.0853,
       "lng": 34.7818
     }
   ]
   ```
4. Coordinates are resolved per apartment:
   - If `street` exists → server-side geocode via Google Maps Geocoding API (using existing `GOOGLE_MAPS_API_KEY`) and cache the result
   - If no street → use static neighborhood lookup table coordinates with small random offset
5. Response is cached for 5 minutes using `Cache-Control` headers
6. Supports `?force=true` query param to bypass cache (for the refresh button)

### Coordinate Resolution

#### Static Neighborhood Lookup

A JSON mapping of `city → area → { lat, lng }` for all known neighborhoods. Covers ~15-20 areas across Tel Aviv, Ramat Gan, and Givatayim. Examples:

| City | Area | Lat | Lng |
|------|------|-----|-----|
| תל אביב | צפון ישן | 32.0853 | 34.7818 |
| תל אביב | פלורנטין | 32.0560 | 34.7700 |
| תל אביב | לב העיר | 32.0700 | 34.7750 |
| תל אביב | הצפון החדש | 32.0900 | 34.7820 |
| תל אביב | נווה צדק | 32.0590 | 34.7650 |
| תל אביב | יד אליהו | 32.0550 | 34.7950 |
| תל אביב | נווה שאנן | 32.0530 | 34.7780 |
| רמת גן | מרכז | 32.0680 | 34.8130 |
| גבעתיים | מרכז | 32.0710 | 34.8100 |

Full table to be populated during implementation by cross-referencing the areas that appear in the Google Sheet.

#### Address Geocoding

When an apartment has a `street` value, the API route geocodes it server-side:
- Call Google Maps Geocoding API with `street + city`
- Cache geocoded coordinates in-memory (per serverless invocation lifetime)
- If geocoding fails, fall back to neighborhood lookup

#### Random Offset for Area-Only Markers

When multiple apartments share the same area and have no street address, apply a deterministic offset (±0.002° lat/lng, ~200m) from the area center to prevent stacking. The offset is derived from a hash of the apartment's unique fields (link URL) so the same apartment always appears at the same position across page reloads.

## Frontend

### Page Structure

Single full-screen page with two sections:

1. **Left Sidebar** (260px wide, dark background `#1a1a2e`)
2. **Map Area** (fills remaining space)

### Sidebar Components (top to bottom)

1. **Header:** "Dira-Bot Map" title
2. **Stats Bar:** Total apartments count + catches count (blue/red badges)
3. **Time Range:** Button group — 24h, 3d, 7d, 30d, All (default: 7d)
4. **Price Range:** Dual-handle slider, 0–10,000₪
5. **Rooms:** Toggle buttons — 2, 2.5, 3, 3.5, 4+ (multi-select)
6. **Catches Only:** Toggle switch
7. **Cities:** Checkboxes — תל אביב, רמת גן, גבעתיים (all checked by default)
8. **Refresh Button:** Forces fresh data pull, shows "Last updated: X min ago"

### Map Behavior

#### Zoomed Out (default view, zoom ≤ 13)

- **Area circles** centered on each neighborhood
- Circle size proportional to number of listings in that area (min 30px, max 80px diameter)
- Circle color: blue (`#3b82f6`) for normal, red (`#ef4444`) if the area contains any catches
- Circle label: listing count + neighborhood name
- Clicking a circle zooms into that area

#### Zoomed In (zoom > 13)

- Area circles dissolve into **individual markers**
- Markers with exact address: pinned to geocoded location
- Markers without address: scattered around area center with random offset
- Marker color: blue for normal, red for catches
- Clicking a marker opens a popup

#### Marker Popup

Compact card showing:
- **Area name** (header)
- **Catch badge** (red "CATCH" pill if applicable)
- **Price** in ₪ format
- **Rooms** count
- **Size** in sqm
- **"View Post →"** button linking to the Facebook URL

### Map Tiles

OpenStreetMap Carto — warm beige background, yellow major roads, green parks, blue water. The default OSM tile layer:
```
https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
```

### Map Center & Zoom

Default center: Tel Aviv metro area (lat: 32.07, lng: 34.79), zoom level 12.

### Mobile Responsiveness

On screens < 768px wide, the sidebar collapses to a bottom drawer that can be swiped up to reveal filters.

## Project Structure

```
map/
├── package.json
├── next.config.js
├── vercel.json                    # (if needed)
├── .env.local                     # Local dev: GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_MAPS_API_KEY
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx               # Main map page
│   │   └── api/
│   │       └── apartments/
│   │           └── route.ts       # API route — fetches from Google Sheets
│   ├── components/
│   │   ├── Map.tsx                # Leaflet map component (dynamic import, no SSR)
│   │   ├── Sidebar.tsx            # Filter sidebar
│   │   ├── ApartmentPopup.tsx     # Marker popup content
│   │   └── AreaCircle.tsx         # Custom area circle overlay
│   ├── lib/
│   │   ├── sheets.ts             # Google Sheets client
│   │   ├── geocode.ts            # Server-side geocoding helper
│   │   └── neighborhoods.ts      # Static area → lat/lng lookup
│   └── types/
│       └── apartment.ts          # TypeScript types
```

## Deployment

### Vercel Setup

1. Create new Vercel project pointing to the `map/` directory (set root directory in Vercel dashboard)
2. Add environment variables:
   - `GOOGLE_SERVICE_ACCOUNT_JSON` — the full JSON key (same content as `service_account.json`)
   - `GOOGLE_SHEET_NAME` — sheet name (default: "Dira-Bot")
   - `GOOGLE_MAPS_API_KEY` — for server-side geocoding of street addresses
3. Deploy — Vercel auto-detects Next.js

### Local Development

```bash
cd map
cp .env.example .env.local
# Fill in GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_MAPS_API_KEY
npm install
npm run dev
```

## Dependencies

- `next` — React framework
- `react`, `react-dom` — UI
- `leaflet`, `react-leaflet` — map rendering
- `@types/leaflet` — TypeScript types
- `google-spreadsheet`, `google-auth-library` — Google Sheets access

## Out of Scope

- User authentication (personal tool, no login needed)
- Writing back to the sheet from the map
- Real-time WebSocket updates (polling/refresh is sufficient)
- Street-level routing or directions
- Historical trend charts or analytics
