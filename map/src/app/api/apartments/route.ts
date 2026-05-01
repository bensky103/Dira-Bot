import { NextRequest, NextResponse } from "next/server";
import { unstable_cache, revalidateTag } from "next/cache";
import { fetchApartments } from "@/lib/sheets";
import { getNeighborhoodCoords } from "@/lib/neighborhoods";
import { hashOffset } from "@/lib/hashOffset";
import type { Apartment } from "@/types/apartment";

// Tag used by action routes (delete/favorite/seen) to invalidate via revalidateTag.
// Must be exported so action routes import a single source of truth.
export const APARTMENTS_CACHE_TAG = "apartments";

// HARD RULE: this route MUST NOT call the Google Geocoding API. Ever.
// Every cold serverless instance previously re-geocoded ~1800 legacy rows,
// which racked up ~1300 NIS in unexpected billing. The Python bot is the
// ONLY place geocoding happens — it writes Lat/Lng/VerifiedCity into the
// sheet once per new listing. This route just reads them.
//
// Legacy rows without coords fall back to a deterministic neighborhood
// lookup (no network calls). To populate them, run the one-shot script:
//   python -m scripts.backfill_geocode --apply
function resolveCoordinates(
  sheetLat: string,
  sheetLng: string,
  sheetVerifiedCity: string,
  city: string,
  area: string,
  link: string
): { lat: number; lng: number; verifiedCity: string | null } {
  // Fast path: coords already persisted in the sheet by the Python bot.
  if (sheetLat && sheetLng) {
    const lat = parseFloat(sheetLat);
    const lng = parseFloat(sheetLng);
    if (!Number.isNaN(lat) && !Number.isNaN(lng)) {
      return { lat, lng, verifiedCity: sheetVerifiedCity || null };
    }
  }

  // Legacy rows: deterministic offline fallback only — NO Google calls.
  const neighborhoodCoords = getNeighborhoodCoords(city, area);
  if (neighborhoodCoords) {
    const offset = hashOffset(link);
    return {
      lat: neighborhoodCoords.lat + offset.dlat,
      lng: neighborhoodCoords.lng + offset.dlng,
      verifiedCity: null,
    };
  }

  // Last resort: Tel Aviv center with a small per-link offset so legacy rows
  // without a known neighborhood don't all stack on one pixel.
  const offset = hashOffset(link);
  return { lat: 32.075 + offset.dlat, lng: 34.78 + offset.dlng, verifiedCity: null };
}

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

async function loadApartments(): Promise<Apartment[]> {
  const rows = await fetchApartments();

  // Synchronous now — no network calls per row. Map directly.
  const apartments: Apartment[] = rows.map((row) => {
    const coords = resolveCoordinates(
      row.lat,
      row.lng,
      row.verifiedCity,
      row.city,
      row.area,
      row.link
    );

    const imageCount = row.images
      ? row.images.split("|").filter(Boolean).length
      : 0;

    return {
      timestamp: row.timestamp,
      city: coords.verifiedCity ?? row.city,
      area: row.area,
      street: row.street,
      price: parseFloat(row.price) || 0,
      rooms: parseFloat(row.rooms) || 0,
      size: parseFloat(row.size) || 0,
      phone: row.phone,
      link: row.link,
      isCatch: String(row.isCatch).toLowerCase() === "true",
      isFavorite: String(row.favorite).toLowerCase() === "true",
      isSeen: String(row.seen).toLowerCase() === "true",
      lat: coords.lat,
      lng: coords.lng,
      hasDescription: Boolean(row.description && row.description.trim().length > 0),
      imageCount,
    };
  });

  spreadOverlappingPins(apartments);

  return apartments.filter((a) => a.price > 0 && a.lat !== 0);
}

// Cached across all serverless instances via Next.js Data Cache.
// Action routes call `revalidateTag(APARTMENTS_CACHE_TAG, { expire: 0 })` to bust it instantly.
const getCachedApartments = unstable_cache(
  loadApartments,
  ["apartments-v1"],
  { tags: [APARTMENTS_CACHE_TAG], revalidate: 5 * 60 }
);

export async function GET(request: NextRequest) {
  try {
    const force = request.nextUrl.searchParams.get("force") === "true";
    // For manual refresh, expire the tag first so the cached call repopulates
    // with fresh data — this also propagates to other instances.
    if (force) revalidateTag(APARTMENTS_CACHE_TAG, { expire: 0 });
    const apartments = await getCachedApartments();

    return NextResponse.json(apartments, {
      headers: {
        "Cache-Control": "private, no-cache, no-store, max-age=0, must-revalidate",
        "X-Cache": force ? "REFRESHED" : "DATA-CACHE",
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
