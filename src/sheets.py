import logging
import os
from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

from src.config import GOOGLE_SHEET_NAME, SHEET_HEADERS, DATA_DIR

STALE_DAYS = 14

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetClient:
    """Google Sheets client for writing and deduplicating listings."""

    def __init__(self):
        sa_path = os.path.join(DATA_DIR, "service_account.json")
        creds = Credentials.from_service_account_file(sa_path, scopes=SCOPES)
        gc = gspread.authorize(creds)
        self._workbook = gc.open(GOOGLE_SHEET_NAME)
        self._sheet = self._workbook.sheet1
        # Read the entire sheet ONCE at startup and reuse it for every
        # initialization step. The previous code did 5 separate reads
        # (ensure_headers, backfill_favorites, backfill_seen, known_links,
        # composite_keys) which burned Sheets API quota for no reason.
        all_rows = self._sheet.get_all_values()
        self._ensure_headers(all_rows)
        self._backfill_columns(all_rows, ["Favorite", "Seen"], default="False")
        # Re-cache caches from in-memory rows (no extra API calls).
        link_col = SHEET_HEADERS.index("Link")
        self._known_links: set[str] = {
            row[link_col] for row in all_rows[1:]
            if len(row) > link_col and row[link_col]
        }
        self._known_composites: set[tuple] = self._composites_from_rows(all_rows)
        # Batch append buffer
        self._pending_rows: list[list] = []

    def _ensure_headers(self, all_rows: list[list[str]]):
        first_row = all_rows[0] if all_rows else []
        if first_row != SHEET_HEADERS:
            # gspread v6 swapped the parameter order: it's now
            # `update(values, range_name)`, not `update(range_name, values)`.
            self._sheet.update([SHEET_HEADERS], "A1")
            # Reflect the change in our in-memory copy so downstream code sees
            # the canonical headers without another network read.
            if all_rows:
                all_rows[0] = list(SHEET_HEADERS)
            else:
                all_rows.append(list(SHEET_HEADERS))

    def _backfill_columns(
        self, all_rows: list[list[str]], headers: list[str], default: str
    ):
        """Backfill empty cells in the given columns with `default`.

        Operates on the in-memory snapshot we already fetched, so the only
        API call is a single batch_update *and only when there is something
        to backfill*. Previously this ran on every cycle even when nothing
        was empty.
        """
        col_indices = {h: SHEET_HEADERS.index(h) for h in headers}
        updates = []
        for i, row in enumerate(all_rows[1:], start=2):  # skip header
            for header, col0 in col_indices.items():
                if len(row) <= col0 or not row[col0].strip():
                    col_letter = chr(64 + col0 + 1)
                    updates.append({
                        "range": f"{col_letter}{i}",
                        "values": [[default]],
                    })
                    # Update the in-memory snapshot so the caches we build
                    # next see the backfilled value.
                    while len(row) <= col0:
                        row.append("")
                    row[col0] = default
        if updates:
            self._sheet.batch_update(updates)
            logger.info(
                "Backfilled %d cells across %s with default=%r",
                len(updates), headers, default,
            )

    @staticmethod
    def _composites_from_rows(all_rows: list[list[str]]) -> set[tuple]:
        """Build the composite-key set from an in-memory rows snapshot."""
        keys: set[tuple] = set()
        street_i = SHEET_HEADERS.index("Street")
        price_i = SHEET_HEADERS.index("Price")
        rooms_i = SHEET_HEADERS.index("Rooms")
        size_i = SHEET_HEADERS.index("Size")
        max_i = max(street_i, price_i, rooms_i, size_i)
        for row in all_rows[1:]:
            if len(row) <= max_i:
                continue
            key = SheetClient._make_composite_key(
                row[street_i], row[price_i], row[rooms_i], row[size_i],
            )
            if key:
                keys.add(key)
        logger.info("Loaded %d composite keys for dedup", len(keys))
        return keys

    def _load_composite_keys(self) -> set[tuple]:
        """Load composite keys from existing sheet rows for cross-group dedup."""
        return self._composites_from_rows(self._sheet.get_all_values())

    @staticmethod
    def _make_composite_key(street, price, rooms, sqm) -> tuple | None:
        """Build a composite key tuple. Returns None if street or price is missing."""
        street = str(street).strip()
        price = str(price).strip()
        rooms = str(rooms).strip()
        sqm = str(sqm).strip()
        if not street or not price:
            return None
        return (street, price, rooms, sqm)

    def is_duplicate_listing(self, parsed: dict) -> bool:
        """Check if a listing with the same street+price+rooms+sqm already exists."""
        key = self._make_composite_key(
            parsed.get("street", ""),
            parsed.get("price_nis", ""),
            parsed.get("rooms", ""),
            parsed.get("sqm", ""),
        )
        if key and key in self._known_composites:
            return True
        return False

    def link_exists(self, link: str) -> bool:
        return link in self._known_links

    def _build_row(
        self,
        parsed: dict,
        link: str,
        images: list[str] | None = None,
        description: str = "",
    ) -> list:
        """Build a sheet row from parsed data."""
        return [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            parsed.get("city", ""),
            parsed.get("area", ""),
            parsed.get("street", ""),
            parsed.get("price_nis", ""),
            parsed.get("rooms", ""),
            parsed.get("sqm", ""),
            parsed.get("phone", ""),
            link,
            str(parsed.get("is_catch", False)),
            "|".join(images) if images else "",
            "False",
            "False",
            description or "",
            parsed.get("lat", ""),
            parsed.get("lng", ""),
            parsed.get("verified_city", ""),
        ]

    def _track_listing(self, parsed: dict, link: str):
        """Update in-memory caches after adding a listing."""
        self._known_links.add(link)
        key = self._make_composite_key(
            parsed.get("street", ""),
            parsed.get("price_nis", ""),
            parsed.get("rooms", ""),
            parsed.get("sqm", ""),
        )
        if key:
            self._known_composites.add(key)

    def append_listing(
        self,
        parsed: dict,
        link: str,
        images: list[str] | None = None,
        description: str = "",
    ):
        if self.link_exists(link):
            logger.info("Duplicate skipped: %s", link)
            return

        row = self._build_row(parsed, link, images, description)
        self._sheet.append_row(row, value_input_option="USER_ENTERED")
        self._track_listing(parsed, link)
        logger.info("Row added: %s – %s", parsed.get("city"), link)

    def queue_listing(
        self,
        parsed: dict,
        link: str,
        images: list[str] | None = None,
        description: str = "",
    ):
        """Queue a listing for batch append. Updates caches immediately for dedup."""
        if self.link_exists(link):
            logger.info("Duplicate skipped: %s", link)
            return False

        row = self._build_row(parsed, link, images, description)
        self._pending_rows.append(row)
        self._track_listing(parsed, link)
        return True

    def flush_pending(self):
        """Append all queued rows to the sheet in a single API call."""
        if not self._pending_rows:
            return 0
        count = len(self._pending_rows)
        self._sheet.append_rows(self._pending_rows, value_input_option="USER_ENTERED")
        logger.info("Batch appended %d rows", count)
        self._pending_rows.clear()
        return count

    def cleanup_stale_rows(self) -> set[str]:
        """Delete rows older than STALE_DAYS and rebuild in-memory caches.

        Returns the set of links that remain in the sheet (for seen_urls sync).
        """
        cutoff = datetime.now() - timedelta(days=STALE_DAYS)
        all_rows = self._sheet.get_all_values()

        # Find row indices to delete (1-indexed, skip header)
        stale_indices = []
        fav_col = SHEET_HEADERS.index("Favorite")
        for i, row in enumerate(all_rows[1:], start=2):
            try:
                # Skip favorited rows — they are immune to cleanup
                if len(row) > fav_col and row[fav_col].strip().lower() == "true":
                    continue
                ts = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                if ts < cutoff:
                    stale_indices.append(i)
            except (ValueError, IndexError):
                continue

        if not stale_indices:
            logger.info("No stale rows to clean up")
            return self._known_links.copy()

        # Group consecutive indices into ranges so a sheet with 200 stale rows
        # becomes a handful of deleteDimension requests instead of 200 writes.
        stale_indices.sort()
        ranges: list[tuple[int, int]] = []
        range_start = range_end = stale_indices[0]
        for idx in stale_indices[1:]:
            if idx == range_end + 1:
                range_end = idx
            else:
                ranges.append((range_start, range_end))
                range_start = range_end = idx
        ranges.append((range_start, range_end))

        # Issue all deletes in a single batch_update API call. Requests are
        # applied in order and shift subsequent indices, so go bottom-to-top.
        requests = [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": self._sheet.id,
                        "dimension": "ROWS",
                        "startIndex": start - 1,  # 0-indexed, inclusive
                        "endIndex": end,          # 0-indexed, exclusive
                    }
                }
            }
            for start, end in reversed(ranges)
        ]
        self._workbook.batch_update({"requests": requests})

        logger.info(
            "Cleaned up %d stale rows in %d range(s) (older than %d days)",
            len(stale_indices), len(ranges), STALE_DAYS,
        )

        # Rebuild caches from the in-memory snapshot we already have, instead
        # of paying for two more sheet reads. The snapshot is `all_rows` minus
        # the indices we just deleted (1-indexed in `stale_indices`, the first
        # data row is index 2).
        deleted_set = set(stale_indices)
        link_col = SHEET_HEADERS.index("Link")
        survivors = [all_rows[0]] + [
            row for i, row in enumerate(all_rows[1:], start=2)
            if i not in deleted_set
        ]
        self._known_links = {
            row[link_col] for row in survivors[1:]
            if len(row) > link_col and row[link_col]
        }
        self._known_composites = self._composites_from_rows(survivors)
        return self._known_links.copy()

    def load_catch_config(self) -> dict | None:
        """Read catch criteria from the Config sheet tab (written by the map UI)."""
        try:
            config_sheet = self._workbook.worksheet("Config")
        except gspread.exceptions.WorksheetNotFound:
            logger.info("No Config tab found — using default catch filters")
            return None

        rows = config_sheet.get_all_values()
        config = {}
        for row in rows[1:]:  # skip header
            if len(row) >= 2:
                config[row[0]] = row[1]

        if "catch_max_price" not in config:
            return None

        result = {
            "max_price": int(config.get("catch_max_price", 0)) or None,
            "min_rooms": float(config.get("catch_min_rooms", 0)) or None,
            "min_sqm": int(config.get("catch_min_sqm", 0)) or None,
            "cities": [c.strip() for c in config.get("catch_cities", "").split(",") if c.strip()] or None,
        }
        logger.info("Loaded catch config from sheet: %s", result)
        return result
