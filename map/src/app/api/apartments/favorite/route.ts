import { NextRequest, NextResponse } from "next/server";
import { GoogleSpreadsheet } from "google-spreadsheet";
import { JWT } from "google-auth-library";
import { invalidateApartmentCache } from "../route";

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

    const rows = await sheet.getRows();
    const favColIndex = sheet.headerValues.indexOf("Favorite");

    if (favColIndex === -1) {
      return NextResponse.json(
        { error: "Favorite column not found in sheet headers" },
        { status: 500 }
      );
    }

    const row = rows.find((r) => r.get("Link") === link);
    if (!row) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    // Write directly to the specific cell via Google Sheets API
    const colLetter = String.fromCharCode(65 + favColIndex);
    const cellRef = `${colLetter}${row.rowNumber}`;
    const value = favorite ? "True" : "False";

    const token = await jwt.authorize();
    const sheetId = process.env.GOOGLE_SHEET_ID!;
    const range = encodeURIComponent(`'${sheet.title}'!${cellRef}`);
    const url = `https://sheets.googleapis.com/v4/spreadsheets/${sheetId}/values/${range}?valueInputOption=USER_ENTERED`;

    const res = await fetch(url, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token.access_token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ values: [[value]] }),
    });

    if (!res.ok) {
      const err = await res.text();
      console.error("[favorite] Sheets API error:", err);
      return NextResponse.json({ error: "Failed to update sheet" }, { status: 500 });
    }

    console.log(`[favorite] wrote "${value}" to cell ${cellRef}`);

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
