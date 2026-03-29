"""Quick debug script: dumps what the bot actually sees on the page."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from playwright.sync_api import sync_playwright

SESSION_FILE = "session.json"
GROUP_URL = "https://www.facebook.com/groups/785935868134249/?sorting_setting=CHRONOLOGICAL"

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

    # Scroll down a few times
    for i in range(5):
        page.evaluate("window.scrollBy(0, window.innerHeight)")
        page.wait_for_timeout(2000)

    # Check what's on the page
    print("\n=== PAGE TITLE ===")
    print(page.title())

    print("\n=== CURRENT URL ===")
    print(page.url)

    print("\n=== TAB STATE ===")
    # Check which tab is active
    tabs = page.query_selector_all('[role="tab"]')
    for tab in tabs:
        name = tab.inner_text().strip()
        selected = tab.get_attribute("aria-selected")
        print(f"  Tab: '{name}' (selected={selected})")

    print("\n=== ROLE=ARTICLE COUNT ===")
    articles = page.query_selector_all('[role="article"]')
    print(f"  Found {len(articles)} articles")
    for i, a in enumerate(articles[:3]):
        text = a.inner_text()[:100].replace("\n", " | ")
        print(f"  Article {i}: {text}")

    print("\n=== ROLE=FEED CHECK ===")
    feeds = page.query_selector_all('[role="feed"]')
    print(f"  Found {len(feeds)} feed containers")
    for i, feed in enumerate(feeds):
        children = feed.query_selector_all(":scope > div")
        print(f"  Feed {i}: {len(children)} direct children")

    print("\n=== ALL CLICKABLE 'See more' / 'ראה עוד' ===")
    see_more = page.evaluate("""() => {
        const results = [];
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
            const text = walker.currentNode.textContent.trim();
            if (text === 'See more' || text === 'ראה עוד' || text === 'עוד') {
                const el = walker.currentNode.parentElement;
                results.push({
                    tag: el.tagName,
                    role: el.getAttribute('role'),
                    class: el.className.substring(0, 50),
                    text: text
                });
            }
        }
        return results;
    }""")
    print(f"  Found {len(see_more)} 'See more' elements")
    for item in see_more[:5]:
        print(f"    <{item['tag']} role={item['role']} class={item['class'][:30]}> '{item['text']}'")

    print("\n=== LOOKING FOR POST CONTAINERS ===")
    # Try various selectors that Facebook might use
    selectors = {
        '[role="article"]': 'role=article',
        '[data-ad-preview]': 'data-ad-preview',
        '[data-pagelet*="FeedUnit"]': 'FeedUnit pagelet',
        '[data-pagelet*="GroupFeed"]': 'GroupFeed pagelet',
        'div[class] > div[class] > div[role="article"]': 'nested articles',
    }
    for sel, label in selectors.items():
        count = len(page.query_selector_all(sel))
        print(f"  {label}: {count}")

    # Dump the feed HTML structure (first level)
    print("\n=== FEED STRUCTURE (first feed, first 5 children) ===")
    structure = page.evaluate("""() => {
        const feed = document.querySelector('[role="feed"]');
        if (!feed) return 'No feed found';
        const children = Array.from(feed.children).slice(0, 5);
        return children.map((c, i) => {
            const article = c.querySelector('[role="article"]');
            const texts = Array.from(c.querySelectorAll('div[dir="auto"]')).map(
                d => d.textContent.substring(0, 80)
            );
            return {
                index: i,
                hasArticle: !!article,
                role: c.getAttribute('role'),
                dirAutoCount: texts.length,
                sampleTexts: texts.slice(0, 3)
            };
        });
    }""")
    if isinstance(structure, str):
        print(f"  {structure}")
    else:
        for item in structure:
            print(f"  Child {item['index']}: article={item['hasArticle']}, "
                  f"role={item['role']}, dir=auto blocks={item['dirAutoCount']}")
            for t in item.get('sampleTexts', []):
                print(f"    text: {t}")

    # Take a screenshot of the current state
    page.screenshot(path="logs/debug_diagnostic.png", full_page=True)
    print("\n=== Screenshot saved to logs/debug_diagnostic.png ===")

    ctx.close()
    browser.close()
    pw.stop()

if __name__ == "__main__":
    main()
