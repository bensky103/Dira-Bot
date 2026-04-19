import { NextRequest, NextResponse } from "next/server";
import { GoogleSpreadsheet } from "google-spreadsheet";
import { JWT } from "google-auth-library";
import { invalidateApartmentCache } from "../route";

async function ensureFavoriteHeader(sheet: InstanceType<typeof import("google-spreadsheet").GoogleSpreadsheetWorksheet>) {
  await sheet.loadHeaderRow();
  const headers = sheet.headerValues;
  if (!headers.includes("Favorite")) {
    await sheet.setHeaderRow([...headers, "Favorite"]);
  }
}

export async function POST(request: NextRequest) {
  try {
    const { link, favorite } = await request.json();
    if (!link || typeof favorite !== "boolean") {
      return NextResponse.json(
        { error: "Missing link or favorite boolean" },
        { status: 400 }
      );
    }

    const creds = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_JSON || "{}");
    const jwt = new JWT({
      email: creds.client_email,
      key: creds.private_key,
      scopes: ["https://www.googleapis.com/auth/spreadsheets"],
    });

    const doc = new GoogleSpreadsheet(process.env.GOOGLE_SHEET_ID!, jwt);
    await doc.loadInfo();

    const sheetName = process.env.GOOGLE_SHEET_NAME || "Dira-Bot";
    const sheet = doc.sheetsByTitle[sheetName] ?? doc.sheetsByIndex[0];

    await ensureFavoriteHeader(sheet);

    const rows = await sheet.getRows();
    console.log("[favorite] headers:", JSON.stringify(sheet.headerValues));
    console.log("[favorite] header count:", sheet.headerValues.length);
    console.log("[favorite] looking for link:", link);
    console.log("[favorite] total rows:", rows.length);

    const row = rows.find((r) => r.get("Link") === link);
    if (!row) {
      console.log("[favorite] row NOT found. Sample links:", rows.slice(0, 3).map(r => r.get("Link")));
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    console.log("[favorite] found row, current Favorite value:", row.get("Favorite"));
    row.set("Favorite", favorite ? "True" : "False");
    await row.save();
    console.log("[favorite] saved successfully, new value:", favorite ? "True" : "False");

    invalidateApartmentCache();

    return NextResponse.json({ ok: true, favorite });
  } catch (error) {
    console.error("Favorite toggle error:", error);
    return NextResponse.json(
      { error: "Failed to toggle favorite" },
      { status: 500 }
    );
  }
}
