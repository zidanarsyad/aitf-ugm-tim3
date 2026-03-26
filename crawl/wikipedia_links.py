import asyncio
import json
import os
from urllib.parse import urljoin
from lxml import html

from crawl4ai import AsyncWebCrawler

BASE_URL = "https://id.wikipedia.org"
START_CATEGORY = "/wiki/Kategori:Pemerintahan_Indonesia"

MAX_DEPTH = 2

visited_categories = set()
article_links = set()
session_scanned = set() # To track categories crawled in the current run


INVALID_PREFIX = (
    "/wiki/Kategori:",
    "/wiki/Berkas:",
    "/wiki/Wikipedia:",
    "/wiki/Bantuan:",
    "/wiki/Portal:",
    "/wiki/Istimewa:",
    "/wiki/Templat:",
    "/w/index.php?title=Kategori:"
)

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db")
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

CHECKPOINT_FILE = os.path.join(DB_DIR, "wikipedia_links_checkpoint.json")
OUTPUT_FILE = os.path.join(DB_DIR, "wikipedia_links.json")

def save_checkpoint():
    checkpoint = {
        "visited_categories": list(visited_categories),
        "article_links": list(article_links)
    }
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=4, ensure_ascii=False)
    print(f"[CHECKPOINT] Saved to {CHECKPOINT_FILE}")

def load_checkpoint():
    global visited_categories, article_links
    
    # 1. First, load existing final data if it exists (for "updatable" support)
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if isinstance(existing_data, list):
                    article_links.update(existing_data)
                    print(f"[INIT] Loaded {len(existing_data)} existing articles from {OUTPUT_FILE}")
        except Exception as e:
            print(f"[ERROR] Failed to load existing output: {e}")

    # 2. Then, load checkpoint if it exists (to resume progress)
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                checkpoint = json.load(f)
                checkpoint_categories = checkpoint.get("visited_categories", [])
                checkpoint_articles = checkpoint.get("article_links", [])
                
                visited_categories.update(checkpoint_categories)
                article_links.update(checkpoint_articles)
                
            print(f"[INIT] Progress resumed: {len(visited_categories)} categories visited, {len(article_links)} total articles.")
        except Exception as e:
            print(f"[ERROR] Failed to load checkpoint: {e}")

async def extract_links_from_html(html_content, current_url):
    """Utility to extract article and category links from a page's HTML."""
    tree = html.fromstring(html_content)
    
    new_articles = set()
    new_subs = set()
    new_pagination = set()

    # 1. Articles
    pages = tree.cssselect("#mw-pages a")
    for a in pages:
        href = a.get("href")
        if href and href.startswith("/wiki/") and not href.startswith(INVALID_PREFIX):
            new_articles.add(urljoin(BASE_URL, href))

    # 2. Subcategories
    subs = tree.cssselect("#mw-subcategories a")
    for a in subs:
        href = a.get("href")
        if href and href.startswith("/wiki/Kategori:"):
            new_subs.add(href)

    # 3. Pagination
    next_pages = tree.xpath("//a[contains(@href,'pagefrom=')]")
    for a in next_pages:
        href = a.get("href")
        if href and href.startswith("/w/index.php"):
            new_pagination.add(href)

    return new_articles, new_subs, new_pagination

async def crawl_batch(crawler, category_paths, depth):
    if depth > MAX_DEPTH or not category_paths:
        return

    # Filter categories to crawl
    to_crawl = []
    for path in category_paths:
        if path in session_scanned:
            continue
        
        # We crawl if:
        # 1. It's never been visited before
        # 2. OR we are at a depth where we need to find its children (resuming/going deeper)
        if path not in visited_categories or depth < MAX_DEPTH:
            to_crawl.append(path)

    if not to_crawl:
        return

    # Mark as scanned in this session and add to visited
    for path in to_crawl:
        session_scanned.add(path)
        visited_categories.add(path)

    urls = [urljoin(BASE_URL, path) for path in to_crawl]
    print(f"[Depth {depth}] Batch crawling {len(urls)} URLs...")

    # Save checkpoint periodically
    if len(visited_categories) % 10 < len(urls):
        save_checkpoint()

    try:
        results = await crawler.arun_many(urls)
        
        all_next_subs = set()
        all_pagination = set()

        for result in results:
            if not result.success:
                print(f"Failed to crawl {result.url}: {result.error_message}")
                continue
            
            articles, subs, pagination = await extract_links_from_html(result.html, result.url)
            
            article_links.update(articles)
            all_next_subs.update(subs)
            all_pagination.update(pagination)

        # 1. Process pagination in current depth
        if all_pagination:
            await crawl_batch(crawler, list(all_pagination), depth)

        # 2. Process subcategories in next depth
        if all_next_subs:
            await crawl_batch(crawler, list(all_next_subs), depth + 1)

    except Exception as e:
        print(f"Error in batch crawl: {e}")

async def main():
    load_checkpoint()

    async with AsyncWebCrawler() as crawler:
        # Initial crawl
        await crawl_batch(crawler, [START_CATEGORY], depth=0)

    print("\n========== FINAL RESULT ==========")
    print("Total artikel ditemukan:", len(article_links))

    data_to_save = sorted(list(article_links))
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        
    print(f"Data final disimpan ke {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
