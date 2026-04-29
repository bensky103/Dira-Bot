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
  images: string;
  favorite: string;
  seen: string;
  description: string;
}

const SCOPES = ["https://www.googleapis.com/auth/spreadsheets"];

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

export interface CatchConfig {
  maxPrice: number;
  minRooms: number;
  minSqm: number;
}

const CONFIG_TAB = "Config";
const CONFIG_HEADERS = ["Key", "Value"];

async function getOrCreateConfigTab(doc: GoogleSpreadsheet) {
  if (doc.sheetsByTitle[CONFIG_TAB]) {
    return doc.sheetsByTitle[CONFIG_TAB];
  }
  const sheet = await doc.addSheet({
    title: CONFIG_TAB,
    headerValues: CONFIG_HEADERS,
  });
  return sheet;
}

export async function fetchCatchConfig(): Promise<CatchConfig | null> {
  const jwt = getAuth();
  const doc = new GoogleSpreadsheet(getSheetId(), jwt);
  await doc.loadInfo();

  const sheet = doc.sheetsByTitle[CONFIG_TAB];
  if (!sheet) return null;

  const rows = await sheet.getRows();
  const config: Record<string, string> = {};
  for (const row of rows) {
    config[row.get("Key")] = row.get("Value");
  }

  if (!config["catch_max_price"]) return null;

  return {
    maxPrice: parseInt(config["catch_max_price"]) || 0,
    minRooms: parseFloat(config["catch_min_rooms"]) || 0,
    minSqm: parseInt(config["catch_min_sqm"]) || 0,
  };
}

export async function saveCatchConfig(config: CatchConfig): Promise<void> {
  const jwt = getAuth();
  const doc = new GoogleSpreadsheet(getSheetId(), jwt);
  await doc.loadInfo();

  const sheet = await getOrCreateConfigTab(doc);
  const rows = await sheet.getRows();

  const entries: Record<string, string> = {
    catch_max_price: String(config.maxPrice),
    catch_min_rooms: String(config.minRooms),
    catch_min_sqm: String(config.minSqm),
  };

  // Update existing rows or add new ones
  const existingKeys = new Set<string>();
  for (const row of rows) {
    const key = row.get("Key");
    if (key in entries) {
      row.set("Value", entries[key]);
      await row.save();
      existingKeys.add(key);
    }
  }

  for (const [key, value] of Object.entries(entries)) {
    if (!existingKeys.has(key)) {
      await sheet.addRow({ Key: key, Value: value });
    }
  }
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
    images: row.get("Images") || "",
    favorite: row.get("Favorite") || "False",
    seen: row.get("Seen") || "False",
    description: row.get("Description") || "",
  }));
}
