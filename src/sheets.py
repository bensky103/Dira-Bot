import logging
import os
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from src.config import GOOGLE_SHEET_NAME, SHEET_HEADERS, DATA_DIR

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
        self._sheet = gc.open(GOOGLE_SHEET_NAME).sheet1
        self._ensure_headers()
        # Cache links in memory to avoid repeated API calls
        self._known_links: set[str] = set(self._sheet.col_values(
            SHEET_HEADERS.index("Link") + 1
        ))

    def _ensure_headers(self):
        first_row = self._sheet.row_values(1)
        if first_row != SHEET_HEADERS:
            self._sheet.update("A1", [SHEET_HEADERS])

    def link_exists(self, link: str) -> bool:
        return link in self._known_links

    def append_listing(self, parsed: dict, link: str):
        if self.link_exists(link):
            logger.info("Duplicate skipped: %s", link)
            return

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            parsed.get("city", ""),
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
        logger.info("Row added: %s – %s", parsed.get("city"), link)
