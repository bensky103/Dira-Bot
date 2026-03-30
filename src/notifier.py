import logging
import requests

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def _send_to_all(msg: str):
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            resp = requests.post(TELEGRAM_API, json={
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "Markdown",
            }, timeout=10)
            if resp.ok:
                logger.info("Telegram sent to %s", chat_id)
            else:
                logger.error("Telegram send to %s failed: %s", chat_id, resp.text)
        except Exception as e:
            logger.error("Telegram send to %s failed: %s", chat_id, e)


def send_catch_alert(parsed: dict, link: str):
    """Send a Telegram alert to all configured chat IDs."""
    msg = (
        "🔥 *דירה מציאה!*\n\n"
        f"📍 *עיר:* {parsed.get('city', 'לא ידוע')}\n"
        f"🏠 *רחוב:* {parsed.get('street', 'לא ידוע')}\n"
        f"💰 *מחיר:* {parsed.get('price_nis', '?'):,} ₪\n"
        f"🛏 *חדרים:* {parsed.get('rooms', '?')}\n"
        f"📐 *מ\"ר:* {parsed.get('sqm', '?')}\n"
        f"📞 *טלפון:* {parsed.get('phone', 'לא צוין')}\n\n"
        f"🔗 [לפוסט המלא]({link})"
    )
    _send_to_all(msg)


SHEET_URL = "https://docs.google.com/spreadsheets/d/1urrmgu-NGkDQaOto671MIpH5ea38pvf1N-bQtCJfTIk/edit?gid=0#gid=0"


def send_batch_alert(count: int):
    """Alert that new listings were added to the sheet."""
    msg = (
        f"📋 *Dira-Bot: {count} דירות חדשות נוספו!*\n\n"
        f"🔗 [פתח את הגיליון]({SHEET_URL})"
    )
    _send_to_all(msg)


def send_session_expired_alert():
    """Alert the user that the Facebook session has expired."""
    msg = (
        "⚠️ *Dira-Bot: Session Expired*\n\n"
        "Facebook session is no longer valid.\n"
        "The bot cannot scrape private groups.\n\n"
        "To fix:\n"
        "1. Stop the bot\n"
        "2. Delete `session.json`\n"
        "3. Run `python run.py` and log in when Firefox opens"
    )
    _send_to_all(msg)
