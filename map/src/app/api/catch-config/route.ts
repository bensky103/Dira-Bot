import { NextRequest, NextResponse } from "next/server";
import { fetchCatchConfig, saveCatchConfig } from "@/lib/sheets";
import type { CatchConfig } from "@/lib/sheets";

export async function GET() {
  try {
    const config = await fetchCatchConfig();
    return NextResponse.json(
      config ?? { maxPrice: 5000, minRooms: 2, minSqm: 50, cities: ["תל אביב"] }
    );
  } catch (error) {
    console.error("Failed to fetch catch config:", error);
    return NextResponse.json(
      { error: "Failed to fetch catch config" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: CatchConfig = await request.json();
    await saveCatchConfig(body);
    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("Failed to save catch config:", error);
    return NextResponse.json(
      { error: "Failed to save catch config" },
      { status: 500 }
    );
  }
}
