# Dira-Bot

Automated apartment hunter for the Israeli rental market. Scrapes Facebook groups, parses listings with AI, filters by your criteria, logs to Google Sheets, and sends Telegram alerts for great deals.

## How It Works

1. **Scrape** — Uses Playwright (Firefox) to browse Facebook groups with a saved login session
2. **Parse** — Sends each post to OpenAI GPT-4o-mini to extract structured data (city, price, rooms, etc.)
3. **Filter** — Applies your criteria (price range, rooms, city, sqm)
4. **Store** — Appends matching listings to a Google Sheet
5. **Alert** — Sends a Telegram message for listings flagged as "catches" (below market rate)
6. **Dedup** — Tracks seen URLs in `seen_urls.json` so posts are never processed twice

## Prerequisites

- Python 3.13+
- A Facebook account (for scraping groups)
- An OpenAI API key
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- A Google Cloud service account with Sheets API enabled

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd Dira-Bot
pip install -r requirements.txt
python -m playwright install firefox
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_IDS` | Comma-separated Telegram chat IDs to receive alerts |
| `GOOGLE_SHEET_NAME` | Name of the Google Sheet to write to (default: `Dira-Bot`) |
| `FB_GROUPS` | Comma-separated Facebook group URLs to scrape |
| `FILTER_MIN_ROOMS` | Minimum rooms (optional) |
| `FILTER_MAX_ROOMS` | Maximum rooms (optional) |
| `FILTER_MIN_SQM` | Minimum sqm (optional) |
| `FILTER_MAX_SQM` | Maximum sqm (optional) |
| `FILTER_MIN_PRICE` | Minimum price in NIS (optional) |
| `FILTER_MAX_PRICE` | Maximum price in NIS (optional) |
| `FILTER_CITIES` | Comma-separated city names in Hebrew (optional) |
| `CYCLE_MINUTES` | Minutes between scrape cycles (default: `20`) |

### 3. Set up Google Sheets

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or select existing)
3. Enable the **Google Sheets API** and **Google Drive API**
4. Go to **Credentials > Create Credentials > Service Account**
5. Create a key (JSON) and save it as `service_account.json` in the project root
6. Create a Google Sheet and share it (Editor) with the service account email (found in the JSON file, looks like `name@project.iam.gserviceaccount.com`)

### 4. Set up Telegram

1. Message [@BotFather](https://t.me/BotFather) on Telegram and create a new bot
2. Copy the bot token to `TELEGRAM_BOT_TOKEN` in `.env`
3. Message your bot, then get your chat ID from `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Add the chat ID to `TELEGRAM_CHAT_IDS` in `.env`

### 5. Run

```bash
python run.py
```

On first run, Firefox will open for you to log into Facebook manually. After login, press ENTER in the terminal. The session is saved to `session.json` and reused for all future headless runs.

### Session Expiry

Facebook sessions expire periodically. When this happens:
1. The bot sends a Telegram alert
2. Stop the bot
3. Delete `session.json`
4. Run `python run.py` and log in again when Firefox opens

## Project Structure

```
Dira-Bot/
├── run.py              # Entry point
├── requirements.txt    # Python dependencies
├── .env.example        # Template for environment variables
└── src/
    ├── config.py       # Loads env vars and filter settings
    ├── scraper.py      # Playwright-based Facebook group scraper
    ├── parser.py       # OpenAI GPT-4o-mini listing parser
    ├── sheets.py       # Google Sheets client
    ├── notifier.py     # Telegram alert sender
    └── main.py         # Main loop: scrape → parse → filter → store → alert
```
