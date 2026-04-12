import { NextRequest, NextResponse } from "next/server";
import { GoogleSpreadsheet } from "google-spreadsheet";
import { JWT } from "google-auth-library";

export async function POST(request: NextRequest) {
  try {
    const { link } = await request.json();
    if (!link) {
      return NextResponse.json({ error: "Missing link" }, { status: 400 });
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

    const row = rows.find((r) => r.get("Link") === link);
    if (!row) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }

    await row.delete();
    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("Delete error:", error);
    return NextResponse.json(
      { error: "Failed to delete" },
      { status: 500 }
    );
  }
}
