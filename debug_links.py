"""Debug: find where post links live in this group's DOM."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright

SESSION_FILE = "session.json"
GROUP_URL = "https://www.facebook.com/groups/287564448778602/?sorting_setting=CHRONOLOGICAL"

def main():
    pw = sync_playwright().start()
    browser = pw.firefox.launch(headless=True)
    ctx = browser.new_context(
        storage_state=SESSION_FILE,
        viewport={"width": 1280, "height": 900},
        locale="he-IL",
    )
    page = ctx.new_page()
    page.goto(GROUP_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(5000)

    for _ in range(3):
        page.evaluate("window.scrollBy(0, window.innerHeight)")
        page.wait_for_timeout(2000)

    # Click "See more" buttons first
    see_more = page.query_selector_all('div[role="button"]:has-text("See more")')
    for btn in see_more[:3]:
        try:
            if btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
        except:
            pass

    result = page.evaluate("""() => {
        const feed = document.querySelector('[role="feed"]');
        if (!feed) return { error: 'No feed found' };

        const children = Array.from(feed.children);
        const output = [];

        for (let i = 0; i < Math.min(children.length, 3); i++) {
            const child = children[i];

            // Check ALL links (not just facebook.com ones)
            const allLinks = Array.from(child.querySelectorAll('a'))
                .map(a => ({
                    href: (a.getAttribute('href') || '').substring(0, 150),
                    text: a.innerText.substring(0, 50),
                    ariaLabel: a.getAttribute('aria-label') || ''
                }))
                .filter(l => l.href);

            // Check for timestamp-like elements (often the permalink)
            const timestamps = Array.from(child.querySelectorAll('a[href] span'))
                .filter(s => {
                    const t = s.innerText.trim();
                    return t.match(/^[0-9]/) || t.includes('hr') || t.includes('min') ||
                           t.includes('Just now') || t.includes('d') || t.includes('שע');
                })
                .map(s => ({
                    text: s.innerText.trim(),
                    parentHref: (s.closest('a') || {}).href || 'no parent link'
                }));

            // Get the HTML of the first link-containing area
            const textPreview = Array.from(child.querySelectorAll('div[dir="auto"]'))
                .map(d => d.innerText.trim())
                .filter(t => t.length > 10)
                .slice(0, 1)
                .join('')
                .substring(0, 80);

            // Check role="article" presence
            const hasArticle = !!child.querySelector('[role="article"]');

            output.push({
                childIndex: i,
                textPreview,
                hasArticle,
                totalLinks: allLinks.length,
                links: allLinks.slice(0, 15),
                timestamps
            });
        }
        return output;
    }""")

    for item in result:
        print(f"\n{'='*60}")
        print(f"Feed child {item['childIndex']} | article={item['hasArticle']}")
        print(f"Text: {item['textPreview']}")
        print(f"\nAll links ({item['totalLinks']}):")
        for link in item['links']:
            label = link.get('ariaLabel', '')
            label_str = f" [{label}]" if label else ""
            text = link.get('text', '')[:30]
            text_str = f" '{text}'" if text else ""
            print(f"  {link['href']}{label_str}{text_str}")
        print(f"\nTimestamp elements:")
        for ts in item['timestamps']:
            print(f"  '{ts['text']}' -> {ts['parentHref']}")

    ctx.close()
    browser.close()
    pw.stop()

if __name__ == "__main__":
    main()
