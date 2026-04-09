import { GoogleSpreadsheet } from "google-spreadsheet";
import { JWT } from "google-auth-library";

interface SheetRow {
  timestamp: string;
  city: string;
  area: string;
  street: string;
  price: string;
  rooms: string;
  size: string;
  phone: string;
  link: string;
  isCatch: string;
}

const SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"];

function getAuth(): JWT {
  const creds = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_JSON || "{}");
  return new JWT({
    email: creds.client_email,
    key: creds.private_key,
    scopes: SCOPES,
  });
}

function getSheetId(): string {
  const id = process.env.GOOGLE_SHEET_ID;
  if (!id) {
    throw new Error("GOOGLE_SHEET_ID env var is required");
  }
  return id;
}

export async function fetchApartments(): Promise<SheetRow[]> {
  const jwt = getAuth();
  const doc = new GoogleSpreadsheet(getSheetId(), jwt);
  await doc.loadInfo();

  const sheetName = process.env.GOOGLE_SHEET_NAME || "Dira-Bot";
  const sheet = doc.sheetsByTitle[sheetName] ?? doc.sheetsByIndex[0];
  const rows = await sheet.getRows();

  return rows.map((row) => ({
    timestamp: row.get("Timestamp") || "",
    city: row.get("City") || "",
    area: row.get("Area") || "",
    street: row.get("Street") || "",
    price: row.get("Price") || "",
    rooms: row.get("Rooms") || "",
    size: row.get("Size") || "",
    phone: row.get("Phone") || "",
    link: row.get("Link") || "",
    isCatch: row.get("Is Catch") || "",
  }));
}
