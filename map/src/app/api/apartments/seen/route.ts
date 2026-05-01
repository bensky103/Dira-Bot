import { NextRequest, NextResponse } from "next/server";
import { updateCellByLink } from "@/lib/sheetActions";

// Same reasoning as the favorite route: toggling "seen" doesn't affect any
// derived field, and the UI already updates optimistically. Skipping
// revalidateTag prevents one click from triggering a full /api/apartments
// rebuild on the next request.
export async function POST(request: NextRequest) {
  try {
    const { link, seen } = await request.json();
    if (!link || typeof seen !== "boolean") {
      return NextResponse.json(
        { error: "Missing link or seen boolean" },
        { status: 400 }
      );
    }

    const ok = await updateCellByLink(link, "Seen", seen ? "True" : "False");
    if (!ok) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    return NextResponse.json({ ok: true, seen });
  } catch (error) {
    console.error("Seen toggle error:", error);
    return NextResponse.json(
      { error: "Failed to toggle seen" },
      { status: 500 }
    );
  }
}
