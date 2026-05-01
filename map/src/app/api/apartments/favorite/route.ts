import { NextRequest, NextResponse } from "next/server";
import { updateCellByLink } from "@/lib/sheetActions";

// Toggling a favorite does not change coordinates or any other field the
// /api/apartments cache returns — and the page already updates optimistically
// (see `handleFavorite` in page.tsx). Skip `revalidateTag` so a single click
// doesn't force a full sheet re-fetch on the next page load.
export async function POST(request: NextRequest) {
  try {
    const { link, favorite } = await request.json();
    if (!link || typeof favorite !== "boolean") {
      return NextResponse.json(
        { error: "Missing link or favorite boolean" },
        { status: 400 }
      );
    }

    const ok = await updateCellByLink(link, "Favorite", favorite ? "True" : "False");
    if (!ok) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({ ok: true, favorite });
  } catch (error) {
    console.error("Favorite toggle error:", error);
    return NextResponse.json(
      { error: "Failed to toggle favorite" },
      { status: 500 }
    );
  }
}