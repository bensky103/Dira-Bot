import { NextRequest, NextResponse } from "next/server";
import { unstable_cache } from "next/cache";
import { fetchApartments } from "@/lib/sheets";
import { APARTMENTS_CACHE_TAG } from "../route";
import type { ApartmentDetails } from "@/types/apartment";

// Lazy-loaded popup details (description + image URLs). Kept out of the main
// list payload so the initial map load stays small. Reuses the same cache
// tag as /api/apartments so any sheet refresh invalidates both at once.
async function loadDetailsMap(): Promise<Record<string, ApartmentDetails>> {
  const rows = await fetchApartments();
  const map: Record<string, ApartmentDetails> = {};
  for (const row of rows) {
    if (!row.link) continue;
    map[row.link] = {
      description: row.description || "",
      images: row.images ? row.images.split("|").filter(Boolean) : [],
    };
  }
  return map;
}

const getCachedDetailsMap = unstable_cache(
  loadDetailsMap,
  ["apartment-details-v1"],
  { tags: [APARTMENTS_CACHE_TAG], revalidate: 5 * 60 }
);

export async function GET(request: NextRequest) {
  const link = request.nextUrl.searchParams.get("link");
  if (!link) {
    return NextResponse.json({ error: "link query param required" }, { status: 400 });
  }

  try {
    const detailsMap = await getCachedDetailsMap();
    const details = detailsMap[link];
    if (!details) {
      return NextResponse.json({ error: "not found" }, { status: 404 });
    }
    return NextResponse.json(details, {
      headers: {
        "Cache-Control": "private, no-cache, no-store, max-age=0, must-revalidate",
      },
    });
  } catch (error) {
    console.error("Details API error:", error);
    return NextResponse.json({ error: "Failed to fetch details" }, { status: 500 });
  }
}
