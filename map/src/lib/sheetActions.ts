// Helpers for the favorite / seen / delete API routes.
//
// Why this exists: the previous implementations called `sheet.getRows()` —
// which fetches every column of every row — just to find the row number for
// one link. With hundreds of rows that's a lot of wasted Sheets API quota and
// bandwidth on every click. These helpers go straight at the Sheets REST API
// using the JWT token: one tiny `values.get` on just the Link column, and one
// `values.update` on the single target cell.

import { JWT } from "google-auth-library";

const SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets";
const SCOPES = ["https://www.googleapis.com/auth/spreadsheets"];

// Cache the column index of each header per process. Header rows don't
// change between requests inside a serverless instance — re-reading them
// every time wastes another API call.
const headerIndexCache = new Map<string, number>();

function getJwt(): JWT {
  const creds = JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_JSON || "{}");
  return new JWT({
    email: creds.client_email,
    key: creds.private_key,
    scopes: SCOPES,
  });
}

function getSheetId(): string {
  const id = process.env.GOOGLE_SHEET_ID;
  if (!id) throw new Error("GOOGLE_SHEET_ID env var is required");
  return id;
}

function getSheetTitle(): string {
  return process.env.GOOGLE_SHEET_NAME || "Dira-Bot";
}

function colLetter(index0: number): string {
  // Supports columns A-Z; sheet only has 17 columns so single-letter is fine.
  return String.fromCharCode(65 + index0);
}

interface SheetsContext {
  token: string;
  sheetId: string;
  sheetTitle: string;
  jwt: JWT;
}

async function getContext(): Promise<SheetsContext> {
  const jwt = getJwt();
  const token = (await jwt.authorize()).access_token;
  if (!token) throw new Error("Failed to authorize Google Sheets JWT");
  return {
    token,
    sheetId: getSheetId(),
    sheetTitle: getSheetTitle(),
    jwt,
  };
}

async function fetchJson(url: string, token: string, init?: RequestInit) {
  const res = await fetch(url, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Sheets API ${res.status}: ${text}`);
  }
  return res.json();
}

/**
 * Resolve the 0-based column index for a header name. Cached per process.
 * Reads only row 1 (the header row).
 */
async function getColumnIndex(
  ctx: SheetsContext,
  header: string
): Promise<number> {
  const key = `${ctx.sheetId}:${ctx.sheetTitle}:${header}`;
  const cached = headerIndexCache.get(key);
  if (cached !== undefined) return cached;

  const range = encodeURIComponent(`'${ctx.sheetTitle}'!1:1`);
  const url = `${SHEETS_BASE}/${ctx.sheetId}/values/${range}`;
  const data = (await fetchJson(url, ctx.token)) as { values?: string[][] };
  const headers = data.values?.[0] ?? [];
  const idx = headers.indexOf(header);
  if (idx === -1) {
    throw new Error(`Header "${header}" not found in sheet`);
  }
  headerIndexCache.set(key, idx);
  return idx;
}

/**
 * Find the 1-based row number whose Link column equals `link`.
 * Reads only the Link column — single small API call, no row data transfer.
 * Returns null if the link is not in the sheet.
 */
async function findRowByLink(
  ctx: SheetsContext,
  link: string
): Promise<number | null> {
  const linkColIndex = await getColumnIndex(ctx, "Link");
  const linkCol = colLetter(linkColIndex);
  const range = encodeURIComponent(
    `'${ctx.sheetTitle}'!${linkCol}2:${linkCol}`
  );
  const url = `${SHEETS_BASE}/${ctx.sheetId}/values/${range}`;
  const data = (await fetchJson(url, ctx.token)) as { values?: string[][] };
  const values = data.values ?? [];
  for (let i = 0; i < values.length; i++) {
    if (values[i][0] === link) {
      return i + 2; // +2: 1-based, plus skipped header row
    }
  }
  return null;
}

/**
 * Update a single cell (header column, row matching link) to `value`.
 * Returns false if the link wasn't found.
 */
export async function updateCellByLink(
  link: string,
  header: string,
  value: string
): Promise<boolean> {
  const ctx = await getContext();
  const [colIndex, rowNumber] = await Promise.all([
    getColumnIndex(ctx, header),
    findRowByLink(ctx, link),
  ]);
  if (rowNumber === null) return false;

  const cell = `${colLetter(colIndex)}${rowNumber}`;
  const range = encodeURIComponent(`'${ctx.sheetTitle}'!${cell}`);
  const url = `${SHEETS_BASE}/${ctx.sheetId}/values/${range}?valueInputOption=USER_ENTERED`;
  await fetchJson(url, ctx.token, {
    method: "PUT",
    body: JSON.stringify({ values: [[value]] }),
  });
  return true;
}

/**
 * Delete the row whose Link column equals `link`. Returns false if not found.
 * Uses `batchUpdate` with a `deleteDimension` request — shifts subsequent rows up.
 */
export async function deleteRowByLink(link: string): Promise<boolean> {
  const ctx = await getContext();
  const rowNumber = await findRowByLink(ctx, link);
  if (rowNumber === null) return false;

  // We need the numeric sheetId (gid), not the spreadsheet id, for batchUpdate.
  const metaUrl = `${SHEETS_BASE}/${ctx.sheetId}?fields=sheets(properties(sheetId,title))`;
  const meta = (await fetchJson(metaUrl, ctx.token)) as {
    sheets?: { properties: { sheetId: number; title: string } }[];
  };
  const sheetMeta = meta.sheets?.find(
    (s) => s.properties.title === ctx.sheetTitle
  );
  if (!sheetMeta) throw new Error(`Sheet tab "${ctx.sheetTitle}" not found`);

  const url = `${SHEETS_BASE}/${ctx.sheetId}:batchUpdate`;
  await fetchJson(url, ctx.token, {
    method: "POST",
    body: JSON.stringify({
      requests: [
        {
          deleteDimension: {
            range: {
              sheetId: sheetMeta.properties.sheetId,
              dimension: "ROWS",
              startIndex: rowNumber - 1, // 0-based, inclusive
              endIndex: rowNumber, // exclusive
            },
          },
        },
      ],
    }),
  });
  return true;
}
