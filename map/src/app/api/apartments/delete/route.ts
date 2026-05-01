import { NextRequest, NextResponse } from "next/server";
import { revalidateTag } from "next/cache";
import { deleteRowByLink } from "@/lib/sheetActions";
import { APARTMENTS_CACHE_TAG } from "../route";

// Delete *does* change the row set returned by /api/apartments, so we still
// invalidate the cache. Coordinates live in the sheet now, so a refresh after
// delete no longer hits Google geocoding - only Google Sheets.
export async function POST(request: NextRequest) {
  try {
    const { link } = await request.json();
    if (!link) {
      return NextResponse.json({ error: "Missing link" }, { status: 400 });
    }

    const ok = await deleteRowByLink(link);
    if (!ok) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    revalidateTag(APARTMENTS_CACHE_TAG, { expire: 0 });
    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("Delete error:", error);
    return NextResponse.json(
      { error: "Failed to delete" },
      { status: 500 }
    );
  }
}