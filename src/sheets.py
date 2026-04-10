import logging
import os
from datetime import datetime, timedelta

import gspread
from google.oauth2.service_account import Credentials

from src.config import GOOGLE_SHEET_NAME, SHEET_HEADERS, DATA_DIR

STALE_DAYS = 21

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
        self._ensure_headers()
        # Cache links in memory to avoid repeated API calls
        self._known_links: set[str] = set(self._sheet.col_values(
            SHEET_HEADERS.index("Link") + 1
        ))
        # Cache composite keys (street, price, rooms, sqm) for cross-group dedup
        self._known_composites: set[tuple] = self._load_composite_keys()

    def _ensure_headers(self):
        first_row = self._sheet.row_values(1)
        if first_row != SHEET_HEADERS:
            self._sheet.update("A1", [SHEET_HEADERS])

    def _load_composite_keys(self) -> set[tuple]:
        """Load composite keys from existing sheet rows for cross-group dedup."""
        keys = set()
        all_rows = self._sheet.get_all_values()
        # Skip header row
        for row in all_rows[1:]:
            if len(row) >= 7:
                street = row[SHEET_HEADERS.index("Street")]
                price = row[SHEET_HEADERS.index("Price")]
                rooms = row[SHEET_HEADERS.index("Rooms")]
                sqm = row[SHEET_HEADERS.index("Size")]
                key = self._make_composite_key(street, price, rooms, sqm)
                if key:
                    keys.add(key)
        logger.info("Loaded %d composite keys for dedup", len(keys))
        return keys

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

    def append_listing(self, parsed: dict, link: str):
        if self.link_exists(link):
            logger.info("Duplicate skipped: %s", link)
            return

        row = [
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
        ]
        self._sheet.append_row(row, value_input_option="USER_ENTERED")
        self._known_links.add(link)
        # Track composite key for cross-group dedup
        key = self._make_composite_key(
            parsed.get("street", ""),
            parsed.get("price_nis", ""),
            parsed.get("rooms", ""),
            parsed.get("sqm", ""),
        )
        if key:
            self._known_composites.add(key)
        logger.info("Row added: %s – %s", parsed.get("city"), link)

    def cleanup_stale_rows(self):
        """Delete rows older than STALE_DAYS and rebuild in-memory caches."""
        cutoff = datetime.now() - timedelta(days=STALE_DAYS)
        all_rows = self._sheet.get_all_values()

        # Find row indices to delete (1-indexed, skip header)
        stale_indices = []
        for i, row in enumerate(all_rows[1:], start=2):
            try:
                ts = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                if ts < cutoff:
                    stale_indices.append(i)
            except (ValueError, IndexError):
                continue

        if not stale_indices:
            logger.info("No stale rows to clean up")
            return

        # Delete from bottom to top so indices don't shift
        for idx in reversed(stale_indices):
            self._sheet.delete_rows(idx)

        logger.info("Cleaned up %d stale rows (older than %d days)", len(stale_indices), STALE_DAYS)

        # Rebuild caches after deletion
        self._known_links = set(self._sheet.col_values(
            SHEET_HEADERS.index("Link") + 1
        ))
        self._known_composites = self._load_composite_keys()

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
