import { NextRequest, NextResponse } from "next/server";
import { unstable_cache, revalidateTag } from "next/cache";
import { fetchApartments } from "@/lib/sheets";
import { geocodeAddress } from "@/lib/geocode";
import { getNeighborhoodCoords } from "@/lib/neighborhoods";
import { reverseGeocodeCity } from "@/lib/reverseGeocode";
import { hashOffset } from "@/lib/hashOffset";
import type { Apartment } from "@/types/apartment";

// Tag used by action routes (delete/favorite/seen) to invalidate via revalidateTag.
// Must be exported so action routes import a single source of truth.
export const APARTMENTS_CACHE_TAG = "apartments";

async function resolveCoordinates(
  street: string,
  city: string,
  area: string,
  link: string
): Promise<{ lat: number; lng: number; verifiedCity: string | null }> {
  // Try geocoding if street exists
  if (street) {
    const geocoded = await geocodeAddress(street, city);
    if (geocoded) {
      const realCity = await reverseGeocodeCity(geocoded.lat, geocoded.lng);
      return { ...geocoded, verifiedCity: realCity };
    }
  }

  // Fall back to neighborhood lookup with deterministic offset
  const neighborhoodCoords = getNeighborhoodCoords(city, area);
  if (neighborhoodCoords) {
    const offset = hashOffset(link);
    return {
      lat: neighborhoodCoords.lat + offset.dlat,
      lng: neighborhoodCoords.lng + offset.dlng,
      verifiedCity: null, // neighborhood coords are already per-city
    };
  }

  // Last resort: Tel Aviv center
  return { lat: 32.075, lng: 34.78, verifiedCity: null };
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
        description: row.description || "",
        lat: coords.lat,
        lng: coords.lng,
        images: row.images ? row.images.split("|").filter(Boolean) : [],
      };
    })
  );

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
