# Dira-Bot Apartment Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive Leaflet map hosted on Vercel that visualizes apartment listings from the Dira-Bot Google Sheet, with area-level clustering, zoom-to-individual-markers, and filtering by time/price/rooms/catches.

**Architecture:** A Next.js App Router project in `map/` with one API route (`/api/apartments`) that reads Google Sheets via `google-spreadsheet` npm package and resolves coordinates. The frontend is a single page with a Leaflet map (dynamically imported to avoid SSR) and a dark filter sidebar.

**Tech Stack:** Next.js (App Router), React, Leaflet, react-leaflet, google-spreadsheet, google-auth-library, TypeScript

**Spec:** `docs/superpowers/specs/2026-04-09-apartment-map-design.md`

---

## File Map

```
map/
├── package.json
├── tsconfig.json
├── next.config.ts
├── .env.example
├── .env.local                          # (gitignored) local dev secrets
├── src/
│   ├── app/
│   │   ├── layout.tsx                  # Root layout, global CSS imports
│   │   ├── page.tsx                    # Main page: renders Sidebar + Map
│   │   ├── globals.css                # Global styles (body, sidebar, map container)
│   │   └── api/
│   │       └── apartments/
│   │           └── route.ts           # GET handler: sheets → geocode → JSON
│   ├── components/
│   │   ├── MapView.tsx                # Leaflet map (client component, dynamic import)
│   │   ├── MapViewDynamic.tsx         # next/dynamic wrapper (no SSR)
│   │   ├── Sidebar.tsx                # Filter sidebar (client component)
│   │   └── ApartmentPopup.tsx         # Popup content for markers
│   ├── lib/
│   │   ├── sheets.ts                  # Google Sheets reader
│   │   ├── geocode.ts                # Google Maps geocoding helper
│   │   ├── neighborhoods.ts          # Static area → lat/lng lookup
│   │   └── hashOffset.ts             # Deterministic offset from link URL hash
│   └── types/
│       └── apartment.ts              # Apartment interface
```

---

## Task 1: Scaffold Next.js Project

**Files:**
- Create: `map/package.json`
- Create: `map/tsconfig.json`
- Create: `map/next.config.ts`
- Create: `map/.env.example`
- Create: `map/.gitignore`

- [ ] **Step 1: Create the `map/` directory and initialize Next.js**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
npx create-next-app@latest map --typescript --app --src-dir --no-tailwind --no-eslint --import-alias "@/*" --use-npm
```

When prompted, accept defaults. This scaffolds a Next.js App Router project with TypeScript.

- [ ] **Step 2: Install dependencies**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot/map"
npm install leaflet react-leaflet google-spreadsheet google-auth-library
npm install -D @types/leaflet
```

- [ ] **Step 3: Create `.env.example`**

Write `map/.env.example`:

```
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"..."}
GOOGLE_SHEET_NAME=Dira-Bot
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
```

- [ ] **Step 4: Create `.env.local` for local development**

Copy the service account JSON from `service_account.json` in the repo root, and your Google Maps API key from `.env`. Write `map/.env.local`:

```
GOOGLE_SERVICE_ACCOUNT_JSON=<paste entire JSON content of service_account.json on one line>
GOOGLE_SHEET_NAME=Dira-Bot
GOOGLE_MAPS_API_KEY=<paste from root .env>
```

- [ ] **Step 5: Update `map/.gitignore`**

Ensure `.env.local` is in `.gitignore` (create-next-app usually includes it, but verify). Also add:

```
.env.local
```

- [ ] **Step 6: Update `map/next.config.ts`**

Replace the contents of `map/next.config.ts` with:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
```

- [ ] **Step 7: Verify the scaffold works**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot/map"
npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 8: Commit**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add map/
git commit -m "feat(map): scaffold Next.js project with dependencies"
```

---

## Task 2: Types and Neighborhood Lookup

**Files:**
- Create: `map/src/types/apartment.ts`
- Create: `map/src/lib/neighborhoods.ts`
- Create: `map/src/lib/hashOffset.ts`

- [ ] **Step 1: Create the Apartment type**

Write `map/src/types/apartment.ts`:

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
  lat: number;
  lng: number;
}
```

- [ ] **Step 2: Create the neighborhood coordinate lookup**

Write `map/src/lib/neighborhoods.ts`:

```typescript
interface Coords {
  lat: number;
  lng: number;
}

const NEIGHBORHOODS: Record<string, Record<string, Coords>> = {
  "תל אביב": {
    "צפון ישן": { lat: 32.0853, lng: 34.7818 },
    "הצפון החדש": { lat: 32.0900, lng: 34.7820 },
    "לב העיר": { lat: 32.0700, lng: 34.7750 },
    "פלורנטין": { lat: 32.0560, lng: 34.7700 },
    "נווה צדק": { lat: 32.0590, lng: 34.7650 },
    "יד אליהו": { lat: 32.0550, lng: 34.7950 },
    "נווה שאנן": { lat: 32.0530, lng: 34.7780 },
    "כרם התימנים": { lat: 32.0680, lng: 34.7660 },
    "שפירא": { lat: 32.0500, lng: 34.7720 },
    "צפון תל אביב": { lat: 32.1050, lng: 34.7900 },
    "הדר יוסף": { lat: 32.1020, lng: 34.8050 },
    "בבלי": { lat: 32.0950, lng: 34.7850 },
    "לב תל אביב": { lat: 32.0750, lng: 34.7800 },
    "מונטיפיורי": { lat: 32.0620, lng: 34.7710 },
    "יפו": { lat: 32.0450, lng: 34.7560 },
  },
  "רמת גן": {
    "מרכז": { lat: 32.0680, lng: 34.8130 },
    "גבול גבעתיים": { lat: 32.0650, lng: 34.8050 },
    "רמת חן": { lat: 32.0850, lng: 34.8100 },
    "תל בנימין": { lat: 32.0780, lng: 34.8200 },
    "נווה יהושע": { lat: 32.0750, lng: 34.8150 },
  },
  "גבעתיים": {
    "מרכז": { lat: 32.0710, lng: 34.8100 },
    "בורוכוב": { lat: 32.0740, lng: 34.8050 },
    "רמת עמידר": { lat: 32.0680, lng: 34.8070 },
  },
};

// Fallback city centers when area is unknown
const CITY_CENTERS: Record<string, Coords> = {
  "תל אביב": { lat: 32.0750, lng: 34.7800 },
  "רמת גן": { lat: 32.0700, lng: 34.8130 },
  "גבעתיים": { lat: 32.0710, lng: 34.8100 },
};

export function getNeighborhoodCoords(
  city: string,
  area: string
): Coords | null {
  return NEIGHBORHOODS[city]?.[area] ?? CITY_CENTERS[city] ?? null;
}
```

- [ ] **Step 3: Create the deterministic hash offset utility**

Write `map/src/lib/hashOffset.ts`:

```typescript
/**
 * Generate a deterministic offset from a string (e.g., link URL).
 * Returns an offset in degrees (~±200m) so markers in the same area
 * don't stack but remain stable across reloads.
 */
export function hashOffset(input: string): { dlat: number; dlng: number } {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    const char = input.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0; // Convert to 32-bit int
  }

  // Use different bits for lat and lng
  const latHash = (hash & 0xffff) / 0xffff; // 0..1
  const lngHash = ((hash >> 16) & 0xffff) / 0xffff; // 0..1

  // ±0.002 degrees ≈ ±200m
  const MAX_OFFSET = 0.002;
  return {
    dlat: (latHash - 0.5) * 2 * MAX_OFFSET,
    dlng: (lngHash - 0.5) * 2 * MAX_OFFSET,
  };
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot/map"
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add map/src/types/ map/src/lib/neighborhoods.ts map/src/lib/hashOffset.ts
git commit -m "feat(map): add apartment types, neighborhood lookup, and hash offset utility"
```

---

## Task 3: Google Sheets Client

**Files:**
- Create: `map/src/lib/sheets.ts`

- [ ] **Step 1: Write the sheets client**

Write `map/src/lib/sheets.ts`:

```typescript
import { GoogleSpreadsheet } from "google-spreadsheet";
import { JWT } from "google-auth-library";

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
}

const SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"];

function getAuth(): JWT {
  const creds = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_JSON || "{}");
  return new JWT({
    email: creds.client_email,
    key: creds.private_key,
    scopes: SCOPES,
  });
}

function getSheetId(): string {
  // The service account JSON contains the sheet URL or we extract the ID
  // from the spreadsheet. We need the spreadsheet ID — get it from the
  // GOOGLE_SHEET_ID env var or parse it from the service account setup.
  const id = process.env.GOOGLE_SHEET_ID;
  if (!id) {
    throw new Error("GOOGLE_SHEET_ID env var is required");
  }
  return id;
}

export async function fetchApartments(): Promise<SheetRow[]> {
  const jwt = getAuth();
  const doc = new GoogleSpreadsheet(getSheetId(), jwt);
  await doc.loadInfo();

  const sheetName = process.env.GOOGLE_SHEET_NAME || "Dira-Bot";
  const sheet = doc.sheetsByTitle[sheetName] ?? doc.sheetsByIndex[0];
  const rows = await sheet.getRows();

  return rows.map((row) => ({
    timestamp: row.get("Timestamp") || "",
    city: row.get("City") || "",
    area: row.get("Area") || "",
    street: row.get("Street") || "",
    price: row.get("Price") || "",
    rooms: row.get("Rooms") || "",
    size: row.get("Size") || "",
    phone: row.get("Phone") || "",
    link: row.get("Link") || "",
    isCatch: row.get("Is Catch") || "",
  }));
}
```

- [ ] **Step 2: Add `GOOGLE_SHEET_ID` to `.env.example`**

Edit `map/.env.example` to add:

```
GOOGLE_SHEET_ID=your_google_sheet_id_from_url
```

The sheet ID is the long string in the Google Sheet URL: `https://docs.google.com/spreadsheets/d/<THIS_PART>/edit`

Also add `GOOGLE_SHEET_ID` to `map/.env.local` with the actual value from your Sheet URL.

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot/map"
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add map/src/lib/sheets.ts map/.env.example
git commit -m "feat(map): add Google Sheets client for reading apartment data"
```

---

## Task 4: Geocoding Helper

**Files:**
- Create: `map/src/lib/geocode.ts`

- [ ] **Step 1: Write the geocoding helper**

Write `map/src/lib/geocode.ts`:

```typescript
const GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json";

// In-memory cache for geocoded coordinates (lives per serverless invocation)
const geocodeCache = new Map<string, { lat: number; lng: number } | null>();

export async function geocodeAddress(
  street: string,
  city: string
): Promise<{ lat: number; lng: number } | null> {
  const apiKey = process.env.GOOGLE_MAPS_API_KEY;
  if (!apiKey || !street || !city) {
    return null;
  }

  const cacheKey = `${street}|${city}`;
  if (geocodeCache.has(cacheKey)) {
    return geocodeCache.get(cacheKey)!;
  }

  try {
    const query = `${street}, ${city}, ישראל`;
    const params = new URLSearchParams({
      address: query,
      key: apiKey,
      language: "he",
      region: "il",
    });

    const resp = await fetch(`${GEOCODE_URL}?${params}`);
    const data = await resp.json();

    if (data.status !== "OK" || !data.results?.length) {
      geocodeCache.set(cacheKey, null);
      return null;
    }

    const location = data.results[0].geometry.location;
    const coords = { lat: location.lat, lng: location.lng };
    geocodeCache.set(cacheKey, coords);
    return coords;
  } catch {
    geocodeCache.set(cacheKey, null);
    return null;
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot/map"
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add map/src/lib/geocode.ts
git commit -m "feat(map): add server-side geocoding helper"
```

---

## Task 5: API Route

**Files:**
- Create: `map/src/app/api/apartments/route.ts`

- [ ] **Step 1: Write the API route**

Write `map/src/app/api/apartments/route.ts`:

```typescript
import { NextRequest, NextResponse } from "next/server";
import { fetchApartments } from "@/lib/sheets";
import { geocodeAddress } from "@/lib/geocode";
import { getNeighborhoodCoords } from "@/lib/neighborhoods";
import { hashOffset } from "@/lib/hashOffset";
import type { Apartment } from "@/types/apartment";

// Simple in-memory cache
let cache: { data: Apartment[]; timestamp: number } | null = null;
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

async function resolveCoordinates(
  street: string,
  city: string,
  area: string,
  link: string
): Promise<{ lat: number; lng: number }> {
  // Try geocoding if street exists
  if (street) {
    const geocoded = await geocodeAddress(street, city);
    if (geocoded) return geocoded;
  }

  // Fall back to neighborhood lookup with deterministic offset
  const neighborhoodCoords = getNeighborhoodCoords(city, area);
  if (neighborhoodCoords) {
    const offset = hashOffset(link);
    return {
      lat: neighborhoodCoords.lat + offset.dlat,
      lng: neighborhoodCoords.lng + offset.dlng,
    };
  }

  // Last resort: Tel Aviv center
  return { lat: 32.075, lng: 34.78 };
}

async function loadApartments(): Promise<Apartment[]> {
  const rows = await fetchApartments();

  const apartments: Apartment[] = await Promise.all(
    rows.map(async (row) => {
      const coords = await resolveCoordinates(
        row.street,
        row.city,
        row.area,
        row.link
      );

      return {
        timestamp: row.timestamp,
        city: row.city,
        area: row.area,
        street: row.street,
        price: parseFloat(row.price) || 0,
        rooms: parseFloat(row.rooms) || 0,
        size: parseFloat(row.size) || 0,
        phone: row.phone,
        link: row.link,
        isCatch: row.isCatch === "True" || row.isCatch === "true",
        lat: coords.lat,
        lng: coords.lng,
      };
    })
  );

  return apartments.filter((a) => a.price > 0 && a.lat !== 0);
}

export async function GET(request: NextRequest) {
  try {
    const force = request.nextUrl.searchParams.get("force") === "true";

    if (!force && cache && Date.now() - cache.timestamp < CACHE_TTL) {
      return NextResponse.json(cache.data, {
        headers: {
          "Cache-Control": "public, s-maxage=300, stale-while-revalidate=60",
          "X-Cache": "HIT",
        },
      });
    }

    const apartments = await loadApartments();
    cache = { data: apartments, timestamp: Date.now() };

    return NextResponse.json(apartments, {
      headers: {
        "Cache-Control": "public, s-maxage=300, stale-while-revalidate=60",
        "X-Cache": "MISS",
      },
    });
  } catch (error) {
    console.error("API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch apartments" },
      { status: 500 }
    );
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot/map"
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add map/src/app/api/
git commit -m "feat(map): add /api/apartments route with caching and geocoding"
```

---

## Task 6: Global Styles

**Files:**
- Modify: `map/src/app/globals.css`
- Modify: `map/src/app/layout.tsx`

- [ ] **Step 1: Replace global styles**

Replace the contents of `map/src/app/globals.css` with:

```css
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html,
body {
  height: 100%;
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    sans-serif;
  overflow: hidden;
}

.page {
  display: flex;
  height: 100vh;
  width: 100vw;
}

/* ── Sidebar ── */
.sidebar {
  width: 260px;
  min-width: 260px;
  background: #1a1a2e;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow-y: auto;
  color: #fff;
  z-index: 1000;
}

.sidebar h1 {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 4px;
}

.sidebar .stats {
  display: flex;
  gap: 8px;
}

.sidebar .stat-card {
  flex: 1;
  background: #2a2a4a;
  border-radius: 8px;
  padding: 8px 10px;
  text-align: center;
}

.sidebar .stat-card .value {
  font-size: 20px;
  font-weight: 700;
}

.sidebar .stat-card .label {
  font-size: 10px;
  color: #888;
}

.sidebar .filter-label {
  font-size: 11px;
  text-transform: uppercase;
  color: #aaa;
  margin-bottom: 6px;
}

.sidebar .btn-group {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.sidebar .btn {
  padding: 4px 10px;
  background: #2a2a4a;
  color: #aaa;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.sidebar .btn.active {
  background: #3b82f6;
  color: #fff;
}

.sidebar .btn:hover {
  background: #3b82f6aa;
  color: #fff;
}

.sidebar .toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #2a2a4a;
  padding: 8px 12px;
  border-radius: 8px;
}

.sidebar .toggle-switch {
  width: 36px;
  height: 20px;
  background: #444;
  border-radius: 10px;
  position: relative;
  cursor: pointer;
  transition: background 0.2s;
}

.sidebar .toggle-switch.on {
  background: #3b82f6;
}

.sidebar .toggle-switch .toggle-knob {
  width: 16px;
  height: 16px;
  background: #fff;
  border-radius: 50%;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: left 0.2s;
}

.sidebar .toggle-switch.on .toggle-knob {
  left: 18px;
}

.sidebar .checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar .checkbox-group label {
  font-size: 12px;
  color: #ccc;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.sidebar .checkbox-group input[type="checkbox"] {
  accent-color: #3b82f6;
}

.sidebar .refresh-btn {
  padding: 8px;
  background: #2a2a4a;
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-radius: 6px;
  text-align: center;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

.sidebar .refresh-btn:hover {
  background: #3b82f6;
  color: #fff;
}

.sidebar .refresh-time {
  font-size: 10px;
  color: #666;
  text-align: center;
  margin-top: 4px;
}

/* ── Price Range Slider ── */
.price-range {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: #ccc;
}

.price-range input[type="range"] {
  flex: 1;
  accent-color: #3b82f6;
}

.price-range .price-value {
  min-width: 50px;
  text-align: center;
  color: #fff;
  font-size: 12px;
}

/* ── Map ── */
.map-container {
  flex: 1;
  height: 100vh;
}

/* ── Leaflet popup overrides ── */
.leaflet-popup-content-wrapper {
  background: #1e293b;
  color: #fff;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  padding: 0;
}

.leaflet-popup-content {
  margin: 0;
  min-width: 180px;
}

.leaflet-popup-tip {
  background: #1e293b;
}

.popup-card {
  padding: 14px;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.popup-header .area-name {
  font-weight: 600;
  font-size: 14px;
}

.popup-header .catch-badge {
  background: #ef4444;
  color: #fff;
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: 600;
}

.popup-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.popup-details .detail-row {
  display: flex;
  justify-content: space-between;
}

.popup-details .detail-label {
  color: #888;
  font-size: 12px;
}

.popup-details .detail-value {
  font-size: 12px;
  font-weight: 600;
}

.popup-link {
  display: block;
  margin-top: 10px;
  text-align: center;
  background: #3b82f6;
  color: #fff;
  padding: 6px;
  border-radius: 5px;
  font-size: 12px;
  text-decoration: none;
  transition: background 0.15s;
}

.popup-link:hover {
  background: #2563eb;
}

/* ── Area Circle Overlay ── */
.area-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.15s;
  border: 2px solid;
}

.area-circle:hover {
  transform: scale(1.1);
}

.area-circle .count {
  font-weight: 700;
  line-height: 1;
}

.area-circle .area-label {
  font-size: 8px;
  opacity: 0.7;
  white-space: nowrap;
}

/* ── Mobile ── */
@media (max-width: 768px) {
  .page {
    flex-direction: column-reverse;
  }

  .sidebar {
    width: 100%;
    min-width: unset;
    height: 45vh;
    max-height: 45vh;
    overflow-y: auto;
  }

  .map-container {
    height: 55vh;
  }
}
```

- [ ] **Step 2: Update layout.tsx**

Replace the contents of `map/src/app/layout.tsx` with:

```tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dira-Bot Map",
  description: "Interactive apartment map for Dira-Bot",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="he" dir="ltr">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add map/src/app/globals.css map/src/app/layout.tsx
git commit -m "feat(map): add global styles and layout"
```

---

## Task 7: Sidebar Component

**Files:**
- Create: `map/src/components/Sidebar.tsx`

- [ ] **Step 1: Write the Sidebar component**

Write `map/src/components/Sidebar.tsx`:

```tsx
"use client";

import { useState, useCallback } from "react";

export interface Filters {
  timeRange: string;
  maxPrice: number;
  rooms: number[];
  catchesOnly: boolean;
  cities: string[];
}

interface SidebarProps {
  totalCount: number;
  catchCount: number;
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  onRefresh: () => void;
  lastUpdated: Date | null;
}

const TIME_OPTIONS = ["24h", "3d", "7d", "30d", "All"];
const ROOM_OPTIONS = [2, 2.5, 3, 3.5, 4];
const CITY_OPTIONS = ["תל אביב", "רמת גן", "גבעתיים"];

export default function Sidebar({
  totalCount,
  catchCount,
  filters,
  onFiltersChange,
  onRefresh,
  lastUpdated,
}: SidebarProps) {
  const [maxPrice, setMaxPrice] = useState(filters.maxPrice);

  const setTimeRange = useCallback(
    (t: string) => onFiltersChange({ ...filters, timeRange: t }),
    [filters, onFiltersChange]
  );

  const toggleRoom = useCallback(
    (r: number) => {
      const rooms = filters.rooms.includes(r)
        ? filters.rooms.filter((x) => x !== r)
        : [...filters.rooms, r];
      onFiltersChange({ ...filters, rooms });
    },
    [filters, onFiltersChange]
  );

  const toggleCatchesOnly = useCallback(
    () =>
      onFiltersChange({ ...filters, catchesOnly: !filters.catchesOnly }),
    [filters, onFiltersChange]
  );

  const toggleCity = useCallback(
    (city: string) => {
      const cities = filters.cities.includes(city)
        ? filters.cities.filter((c) => c !== city)
        : [...filters.cities, city];
      onFiltersChange({ ...filters, cities });
    },
    [filters, onFiltersChange]
  );

  const handlePriceChange = useCallback(
    (val: number) => {
      setMaxPrice(val);
      onFiltersChange({ ...filters, maxPrice: val });
    },
    [filters, onFiltersChange]
  );

  const timeAgo = lastUpdated
    ? `${Math.round((Date.now() - lastUpdated.getTime()) / 60000)} min ago`
    : "never";

  return (
    <div className="sidebar">
      <h1>🏠 Dira-Bot Map</h1>

      {/* Stats */}
      <div className="stats">
        <div className="stat-card">
          <div className="value" style={{ color: "#3b82f6" }}>
            {totalCount}
          </div>
          <div className="label">Apartments</div>
        </div>
        <div className="stat-card">
          <div className="value" style={{ color: "#ef4444" }}>
            {catchCount}
          </div>
          <div className="label">Catches</div>
        </div>
      </div>

      {/* Time Range */}
      <div>
        <div className="filter-label">Time Range</div>
        <div className="btn-group">
          {TIME_OPTIONS.map((t) => (
            <button
              key={t}
              className={`btn ${filters.timeRange === t ? "active" : ""}`}
              onClick={() => setTimeRange(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Price Range */}
      <div>
        <div className="filter-label">Max Price (₪)</div>
        <div className="price-range">
          <span className="price-value">0</span>
          <input
            type="range"
            min={0}
            max={10000}
            step={500}
            value={maxPrice}
            onChange={(e) => handlePriceChange(Number(e.target.value))}
          />
          <span className="price-value">
            {maxPrice === 10000 ? "10k+" : maxPrice.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Rooms */}
      <div>
        <div className="filter-label">Rooms</div>
        <div className="btn-group">
          {ROOM_OPTIONS.map((r) => (
            <button
              key={r}
              className={`btn ${filters.rooms.includes(r) ? "active" : ""}`}
              onClick={() => toggleRoom(r)}
            >
              {r === 4 ? "4+" : r}
            </button>
          ))}
        </div>
      </div>

      {/* Catches Only */}
      <div className="toggle-row">
        <span style={{ fontSize: 13 }}>🔥 Catches only</span>
        <div
          className={`toggle-switch ${filters.catchesOnly ? "on" : ""}`}
          onClick={toggleCatchesOnly}
        >
          <div className="toggle-knob" />
        </div>
      </div>

      {/* Cities */}
      <div>
        <div className="filter-label">Cities</div>
        <div className="checkbox-group">
          {CITY_OPTIONS.map((city) => (
            <label key={city}>
              <input
                type="checkbox"
                checked={filters.cities.includes(city)}
                onChange={() => toggleCity(city)}
              />
              {city}
            </label>
          ))}
        </div>
      </div>

      {/* Refresh */}
      <div style={{ marginTop: "auto" }}>
        <button className="refresh-btn" onClick={onRefresh}>
          🔄 Refresh Data
        </button>
        <div className="refresh-time">Last updated: {timeAgo}</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot/map"
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add map/src/components/Sidebar.tsx
git commit -m "feat(map): add filter sidebar component"
```

---

## Task 8: Popup Component

**Files:**
- Create: `map/src/components/ApartmentPopup.tsx`

- [ ] **Step 1: Write the popup component**

Write `map/src/components/ApartmentPopup.tsx`:

```tsx
import type { Apartment } from "@/types/apartment";

interface ApartmentPopupProps {
  apartment: Apartment;
}

export default function ApartmentPopup({ apartment }: ApartmentPopupProps) {
  return (
    <div className="popup-card">
      <div className="popup-header">
        <span className="area-name">{apartment.area}</span>
        {apartment.isCatch && <span className="catch-badge">🔥 CATCH</span>}
      </div>
      <div className="popup-details">
        <div className="detail-row">
          <span className="detail-label">Price</span>
          <span className="detail-value">
            ₪{apartment.price.toLocaleString()}
          </span>
        </div>
        <div className="detail-row">
          <span className="detail-label">Rooms</span>
          <span className="detail-value">{apartment.rooms}</span>
        </div>
        {apartment.size > 0 && (
          <div className="detail-row">
            <span className="detail-label">Size</span>
            <span className="detail-value">{apartment.size} sqm</span>
          </div>
        )}
      </div>
      <a
        className="popup-link"
        href={apartment.link}
        target="_blank"
        rel="noopener noreferrer"
      >
        View Post →
      </a>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add map/src/components/ApartmentPopup.tsx
git commit -m "feat(map): add apartment popup component"
```

---

## Task 9: Map Component

**Files:**
- Create: `map/src/components/MapView.tsx`
- Create: `map/src/components/MapViewDynamic.tsx`

- [ ] **Step 1: Write the MapView component**

Write `map/src/components/MapView.tsx`:

```tsx
"use client";

import { useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Marker,
  Popup,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Apartment } from "@/types/apartment";
import ApartmentPopup from "./ApartmentPopup";

// Fix Leaflet default marker icon issue with bundlers
const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const catchIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
  className: "catch-marker",
});

interface AreaCluster {
  city: string;
  area: string;
  lat: number;
  lng: number;
  count: number;
  hasCatch: boolean;
  apartments: Apartment[];
}

const ZOOM_THRESHOLD = 13;

function ZoomTracker({ onZoomChange }: { onZoomChange: (z: number) => void }) {
  useMapEvents({
    zoomend: (e) => onZoomChange(e.target.getZoom()),
  });
  return null;
}

interface MapViewProps {
  apartments: Apartment[];
}

export default function MapView({ apartments }: MapViewProps) {
  const [zoom, setZoom] = useState(12);

  // Group apartments by city+area for area circles
  const clusters = useMemo(() => {
    const map = new Map<string, AreaCluster>();
    for (const apt of apartments) {
      const key = `${apt.city}|${apt.area}`;
      if (!map.has(key)) {
        // Use first apartment's coords as area center (approximation)
        map.set(key, {
          city: apt.city,
          area: apt.area,
          lat: apt.lat,
          lng: apt.lng,
          count: 0,
          hasCatch: false,
          apartments: [],
        });
      }
      const cluster = map.get(key)!;
      cluster.count++;
      if (apt.isCatch) cluster.hasCatch = true;
      cluster.apartments.push(apt);
      // Average the coordinates for better center
      cluster.lat =
        (cluster.lat * (cluster.count - 1) + apt.lat) / cluster.count;
      cluster.lng =
        (cluster.lng * (cluster.count - 1) + apt.lng) / cluster.count;
    }
    return Array.from(map.values());
  }, [apartments]);

  const showClusters = zoom <= ZOOM_THRESHOLD;

  return (
    <MapContainer
      center={[32.07, 34.79]}
      zoom={12}
      className="map-container"
      style={{ height: "100%", width: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ZoomTracker onZoomChange={setZoom} />

      {showClusters
        ? clusters.map((cluster) => {
            const radius = Math.min(
              40,
              Math.max(15, 10 + cluster.count * 2)
            );
            const color = cluster.hasCatch ? "#ef4444" : "#3b82f6";
            return (
              <CircleMarker
                key={`${cluster.city}|${cluster.area}`}
                center={[cluster.lat, cluster.lng]}
                radius={radius}
                pathOptions={{
                  fillColor: color,
                  fillOpacity: 0.35,
                  color: color,
                  weight: 2,
                }}
              >
                <Popup>
                  <div className="popup-card">
                    <div className="popup-header">
                      <span className="area-name">
                        {cluster.area} ({cluster.city})
                      </span>
                    </div>
                    <div className="popup-details">
                      <div className="detail-row">
                        <span className="detail-label">Listings</span>
                        <span className="detail-value">{cluster.count}</span>
                      </div>
                      {cluster.hasCatch && (
                        <div className="detail-row">
                          <span className="detail-label">Catches</span>
                          <span
                            className="detail-value"
                            style={{ color: "#ef4444" }}
                          >
                            {
                              cluster.apartments.filter((a) => a.isCatch)
                                .length
                            }
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })
        : apartments.map((apt, i) => (
            <Marker
              key={`${apt.link}-${i}`}
              position={[apt.lat, apt.lng]}
              icon={apt.isCatch ? catchIcon : defaultIcon}
            >
              <Popup>
                <ApartmentPopup apartment={apt} />
              </Popup>
            </Marker>
          ))}
    </MapContainer>
  );
}
```

- [ ] **Step 2: Add catch-marker CSS to globals.css**

Append to the end of `map/src/app/globals.css`:

```css

/* Catch marker — red tint via CSS filter */
.catch-marker {
  filter: hue-rotate(140deg) saturate(3);
}
```

- [ ] **Step 3: Create the dynamic import wrapper**

Write `map/src/components/MapViewDynamic.tsx`:

```tsx
"use client";

import dynamic from "next/dynamic";
import type { Apartment } from "@/types/apartment";

const MapView = dynamic(() => import("./MapView"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        flex: 1,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f2efe9",
        color: "#666",
      }}
    >
      Loading map...
    </div>
  ),
});

export default function MapViewDynamic({
  apartments,
}: {
  apartments: Apartment[];
}) {
  return <MapView apartments={apartments} />;
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot/map"
npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 5: Commit**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add map/src/components/MapView.tsx map/src/components/MapViewDynamic.tsx map/src/app/globals.css
git commit -m "feat(map): add Leaflet map component with area circles and individual markers"
```

---

## Task 10: Main Page — Wire Everything Together

**Files:**
- Modify: `map/src/app/page.tsx`

- [ ] **Step 1: Write the main page**

Replace the contents of `map/src/app/page.tsx` with:

```tsx
"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import Sidebar, { type Filters } from "@/components/Sidebar";
import MapViewDynamic from "@/components/MapViewDynamic";
import type { Apartment } from "@/types/apartment";

const DEFAULT_FILTERS: Filters = {
  timeRange: "7d",
  maxPrice: 10000,
  rooms: [],
  catchesOnly: false,
  cities: ["תל אביב", "רמת גן", "גבעתיים"],
};

function getTimeThreshold(range: string): Date {
  const now = new Date();
  switch (range) {
    case "24h":
      return new Date(now.getTime() - 24 * 60 * 60 * 1000);
    case "3d":
      return new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000);
    case "7d":
      return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    case "30d":
      return new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    default:
      return new Date(0); // "All"
  }
}

export default function Home() {
  const [apartments, setApartments] = useState<Apartment[]>([]);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async (force = false) => {
    setLoading(true);
    try {
      const url = force ? "/api/apartments?force=true" : "/api/apartments";
      const res = await fetch(url);
      if (!res.ok) throw new Error("Fetch failed");
      const data: Apartment[] = await res.json();
      setApartments(data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Failed to fetch apartments:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filtered = useMemo(() => {
    const threshold = getTimeThreshold(filters.timeRange);

    return apartments.filter((apt) => {
      // Time filter
      if (apt.timestamp && new Date(apt.timestamp) < threshold) return false;

      // Price filter
      if (filters.maxPrice < 10000 && apt.price > filters.maxPrice)
        return false;

      // Rooms filter (empty = all rooms)
      if (filters.rooms.length > 0) {
        const matchesRoom = filters.rooms.some((r) =>
          r === 4 ? apt.rooms >= 4 : apt.rooms === r
        );
        if (!matchesRoom) return false;
      }

      // Catches only
      if (filters.catchesOnly && !apt.isCatch) return false;

      // City filter
      if (!filters.cities.includes(apt.city)) return false;

      return true;
    });
  }, [apartments, filters]);

  const catchCount = filtered.filter((a) => a.isCatch).length;

  return (
    <div className="page">
      <Sidebar
        totalCount={filtered.length}
        catchCount={catchCount}
        filters={filters}
        onFiltersChange={setFilters}
        onRefresh={() => fetchData(true)}
        lastUpdated={lastUpdated}
      />
      {loading && apartments.length === 0 ? (
        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "#f2efe9",
            color: "#666",
            fontSize: 16,
          }}
        >
          Loading apartments...
        </div>
      ) : (
        <MapViewDynamic apartments={filtered} />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify the build succeeds**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot/map"
npm run build
```

Expected: Build succeeds. (API route may warn about missing env vars at build time — that's OK, it runs server-side only.)

- [ ] **Step 3: Commit**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add map/src/app/page.tsx
git commit -m "feat(map): wire up main page with sidebar, filters, and map"
```

---

## Task 11: Local Smoke Test

- [ ] **Step 1: Set up `.env.local`**

Ensure `map/.env.local` has all required values:

```
GOOGLE_SERVICE_ACCOUNT_JSON=<entire content of service_account.json on one line>
GOOGLE_SHEET_ID=<sheet ID from your Google Sheet URL>
GOOGLE_SHEET_NAME=Dira-Bot
GOOGLE_MAPS_API_KEY=<your key from root .env>
```

- [ ] **Step 2: Run the dev server**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot/map"
npm run dev
```

- [ ] **Step 3: Open http://localhost:3000 and verify**

Check:
- Map loads with OSM tiles centered on Tel Aviv area
- Sidebar is visible on the left with filters
- Area circles appear (if sheet has data)
- Clicking time range / rooms / cities filters updates the map
- Zooming past level 13 shows individual markers
- Clicking a marker shows the popup with price/rooms/size/link
- Refresh button works
- No console errors

- [ ] **Step 4: Fix any issues found during smoke test**

Address any bugs discovered during testing.

- [ ] **Step 5: Commit any fixes**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add map/
git commit -m "fix(map): address issues from local smoke test"
```

---

## Task 12: Add `.superpowers/` to `.gitignore`

**Files:**
- Modify: `.gitignore` (repo root)

- [ ] **Step 1: Add `.superpowers/` to root `.gitignore`**

Append to the repo root `.gitignore`:

```
# Superpowers brainstorm files
.superpowers/
```

- [ ] **Step 2: Commit**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add .gitignore
git commit -m "chore: add .superpowers/ to gitignore"
```

---

## Task 13: Deploy to Vercel

- [ ] **Step 1: Install Vercel CLI (if not already installed)**

```bash
npm install -g vercel
```

- [ ] **Step 2: Link and deploy**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot/map"
vercel
```

When prompted:
- Set up and deploy? **Y**
- Which scope? Select your account
- Link to existing project? **N**
- Project name? `dira-bot-map`
- Directory with source code? `./` (current directory, which is `map/`)
- Override settings? **N** (Next.js is auto-detected)

- [ ] **Step 3: Set environment variables on Vercel**

```bash
vercel env add GOOGLE_SERVICE_ACCOUNT_JSON production
vercel env add GOOGLE_SHEET_ID production
vercel env add GOOGLE_SHEET_NAME production
vercel env add GOOGLE_MAPS_API_KEY production
```

Paste the values when prompted (same values as your `.env.local`).

- [ ] **Step 4: Redeploy with environment variables**

```bash
vercel --prod
```

- [ ] **Step 5: Verify the deployed URL**

Open the Vercel URL in a browser and confirm:
- Map loads with apartment data
- Filters work
- Popups show correct information

- [ ] **Step 6: Commit any deployment config changes**

```bash
cd "c:/Users/Guy Bensky/Desktop/Elevize/Dira-Bot"
git add map/
git commit -m "chore(map): add Vercel deployment config"
```
