import os
import random
import logging
from playwright.sync_api import sync_playwright, Browser, BrowserContext

logger = logging.getLogger(__name__)

from src.config import DATA_DIR

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
SESSION_FILE = os.path.join(DATA_DIR, "session.json")


class Scraper:
    """Facebook group scraper using Firefox (avoids Arkose Labs CAPTCHA)."""

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    @property
    def playwright(self):
        return self._playwright

    def start(self):
        self._playwright = sync_playwright().start()

        if os.path.exists(SESSION_FILE):
            logger.info("Found saved session, launching headless...")
            self._browser = self._playwright.firefox.launch(headless=True)
            self._context = self._browser.new_context(
                storage_state=SESSION_FILE,
                viewport={"width": 1280, "height": 900},
                locale="he-IL",
            )
        else:
            logger.info("No session found — opening Firefox for manual login...")
            self._browser = self._playwright.firefox.launch(headless=False)
            self._context = self._browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="he-IL",
            )
            self._manual_login()

    def _manual_login(self):
        page = self._context.new_page()
        page.goto("https://www.facebook.com/")
        logger.info("========================================")
        logger.info("  Log in to Facebook in the browser.")
        logger.info("  Complete 2FA if needed.")
        logger.info("  Once you see the News Feed,")
        logger.info("  come back here and press ENTER.")
        logger.info("========================================")
        input("\n>>> Press ENTER after you are logged in: ")
        self._context.storage_state(path=SESSION_FILE)
        logger.info("Session saved to %s", SESSION_FILE)
        page.close()

        # Restart headless now that we have a session
        self._context.close()
        self._browser.close()
        logger.info("Restarting headless...")
        self._browser = self._playwright.firefox.launch(headless=True)
        self._context = self._browser.new_context(
            storage_state=SESSION_FILE,
            viewport={"width": 1280, "height": 900},
            locale="he-IL",
        )

    def scrape_group(self, group_url: str) -> list[dict]:
        """Scrape posts from a single Facebook group. Returns list of {text, url}."""
        page = self._context.new_page()
        posts = []
        try:
            url = group_url.rstrip("/") + "?sorting_setting=CHRONOLOGICAL"
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(5000)

            # Dismiss popups
            for selector in [
                '[aria-label="Close"]',
                '[aria-label="סגירה"]',
                '[data-cookiebanner="accept_button"]',
                '[role="button"]:has-text("Not Now")',
                '[role="button"]:has-text("לא עכשיו")',
            ]:
                try:
                    btn = page.query_selector(selector)
                    if btn and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(500)
                except Exception:
                    pass

            # Scroll to load posts
            for i in range(10):
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                page.wait_for_timeout(random.randint(2000, 4000))

            # Check if we're actually logged in / seeing content
            has_feed = page.query_selector('[role="feed"]') is not None
            if not has_feed:
                logger.warning("No feed found on %s — session likely expired", group_url)
                return []

            # Click all "See more" to expand truncated posts
            see_more = page.query_selector_all(
                'div[role="button"]:has-text("See more"), '
                'div[role="button"]:has-text("ראה עוד")'
            )
            logger.info("Expanding %d 'See more' buttons", len(see_more))
            for btn in see_more:
                try:
                    if btn.is_visible():
                        btn.scroll_into_view_if_needed()
                        btn.click()
                        page.wait_for_timeout(300)
                except Exception:
                    pass
            # Wait for expanded content to render
            if see_more:
                page.wait_for_timeout(1000)

            # Extract posts from feed children (not role="article" — Facebook
            # doesn't always use that role on group post containers)
            posts = page.evaluate("""() => {
                const feed = document.querySelector('[role="feed"]');
                if (!feed) return [];

                const results = [];
                const children = Array.from(feed.children);

                for (const child of children) {
                    // Get all text blocks in this post (dir="auto" is where FB puts text)
                    const textBlocks = Array.from(
                        child.querySelectorAll('div[dir="auto"]')
                    );

                    // Filter out comment text: comments are inside a form or
                    // after ul[role] elements
                    const commentForm = child.querySelector('form');
                    const commentSection = child.querySelector('ul');

                    let cutoffY = Infinity;
                    if (commentForm) {
                        const rect = commentForm.getBoundingClientRect();
                        cutoffY = Math.min(cutoffY, rect.top);
                    }
                    if (commentSection) {
                        const rect = commentSection.getBoundingClientRect();
                        cutoffY = Math.min(cutoffY, rect.top);
                    }

                    const parts = [];
                    for (const block of textBlocks) {
                        const rect = block.getBoundingClientRect();
                        // Only include text above comments
                        if (rect.top >= cutoffY) continue;

                        const text = block.innerText.trim();
                        // Skip short fragments (buttons, timestamps, etc.)
                        if (text.length < 10) continue;
                        // Skip known UI text
                        if (['Like', 'Reply', 'Share', 'Comment', 'See more',
                             'ראה עוד', 'Write a comment'].includes(text)) continue;
                        parts.push(text);
                    }

                    const postText = parts.join('\\n');
                    if (postText.length < 30) continue;

                    // Find post URL — check multiple FB URL patterns
                    // Helper to normalize FB hrefs into full URLs
                    const normalizeHref = (href) => {
                        const clean = href.split('?')[0];
                        return clean.startsWith('/')
                            ? 'https://www.facebook.com' + clean
                            : clean;
                    };

                    // Extract group slug from the page URL for building permalinks
                    const pageUrl = window.location.href;
                    const groupMatch = pageUrl.match(/groups\\/([^\\/?]+)/);
                    const groupSlug = groupMatch ? groupMatch[1] : '';

                    let postUrl = '';
                    const links = child.querySelectorAll('a[href]');
                    const allHrefs = Array.from(links).map(l => l.getAttribute('href') || '');

                    // 1. Explicit post-URL patterns (commerce listings, posts, permalinks)
                    for (const href of allHrefs) {
                        if (href.includes('/posts/') ||
                            href.includes('/permalink/') ||
                            href.includes('/story.php') ||
                            href.includes('/commerce/listing/') ||
                            href.includes('/marketplace/item/')) {
                            postUrl = normalizeHref(href);
                            break;
                        }
                    }

                    // 2. Any link with a numeric post/listing ID
                    if (!postUrl) {
                        for (const href of allHrefs) {
                            if (/groups\\/[^/]+\\/posts\\/[0-9]+/.test(href) ||
                                /groups\\/[0-9]+\\/[0-9]+/.test(href) ||
                                /listing\\/[0-9]+/.test(href)) {
                                postUrl = normalizeHref(href);
                                break;
                            }
                        }
                    }

                    // 3. Last resort: hash the post text for a unique ID.
                    //    This prevents using the bare group URL (which breaks
                    //    deduplication — every linkless post would share the
                    //    same "URL" and only the first would ever be stored).
                    if (!postUrl) {
                        let hash = 0;
                        for (let i = 0; i < postText.length; i++) {
                            hash = ((hash << 5) - hash) + postText.charCodeAt(i);
                            hash |= 0;
                        }
                        postUrl = '__no_link__' + Math.abs(hash).toString(36);
                    }

                    // Extract post images (not profile pics / UI icons)
                    const images = [];
                    const seen = new Set();
                    const imgElements = child.querySelectorAll('img');
                    for (const img of imgElements) {
                        // Check multiple attributes — FB lazy-loads with data-src
                        const src = img.getAttribute('src') || '';
                        const dataSrc = img.getAttribute('data-src') || '';
                        const dataSrcFallback = img.getAttribute('data-src-fallback') || '';
                        const url = [src, dataSrc, dataSrcFallback]
                            .find(s => s.includes('scontent'));
                        if (!url) continue;
                        // Dedupe (same image can appear in multiple attributes)
                        if (seen.has(url)) continue;
                        seen.add(url);
                        // Skip images in the comment section
                        const rect = img.getBoundingClientRect();
                        if (rect.top >= cutoffY) continue;
                        // Skip tiny images only if they have rendered dimensions
                        // (lazy-loaded images may be 0x0 but still valid)
                        if (rect.width > 0 && rect.height > 0 &&
                            rect.width < 50 && rect.height < 50) continue;
                        images.push(url);
                    }

                    results.push({
                        text: postText,
                        url: postUrl,
                        images: images
                    });
                }
                return results;
            }""")

            # Log posts with missing links for debugging
            no_link = sum(1 for p in posts if p["url"].startswith("__no_link__"))
            if no_link:
                logger.warning("%d/%d posts had no extractable link", no_link, len(posts))

            logger.info("Extracted %d posts from %s", len(posts), group_url)

            # Debug screenshot
            debug_dir = os.path.join(PROJECT_DIR, "logs")
            os.makedirs(debug_dir, exist_ok=True)
            group_id = group_url.rstrip("/").split("/")[-1]
            page.screenshot(
                path=os.path.join(debug_dir, f"debug_{group_id}.png"),
                full_page=True,
            )

        except Exception as e:
            logger.error("Error scraping %s: %s", group_url, e)
        finally:
            page.close()

        return posts

    def close(self):
        if self._context:
            try:
                self._context.storage_state(path=SESSION_FILE)
            except Exception:
                pass
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
