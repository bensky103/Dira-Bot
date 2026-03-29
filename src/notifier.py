import logging
from telegram import Bot

from src.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS

logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def send_catch_alert(parsed: dict, link: str):
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
    await _send_to_all(msg)


async def send_session_expired_alert():
    """Alert the user that the Facebook session has expired."""
    msg = (
        "⚠️ *Dira-Bot: Session Expired*\n\n"
        "Facebook session is no longer valid.\n"
        "The bot cannot scrape private groups.\n\n"
        "To fix:\n"
        "1. Run `python run.py` locally\n"
        "2. Log in when Firefox opens\n"
        "3. Update the `SESSION_JSON` env var on Railway\n"
        "4. Delete `/data/session.json` from the volume and redeploy"
    )
    await _send_to_all(msg)


async def _send_to_all(msg: str):
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode="Markdown",
            )
            logger.info("Telegram sent to %s", chat_id)
        except Exception as e:
            logger.error("Telegram send to %s failed: %s", chat_id, e)
