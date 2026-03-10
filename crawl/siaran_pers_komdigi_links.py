"""
crawl/siaran_pers_komdigi_links.py
Scrape link lists from Komdigi portal.

Changes from original:
- Integrated deduplication directly (fixed bug where dedup key was 'page', now 'link')
- Schema from core/schemas.py
- Writes deduplicated links to DB_DIR/siaran_pers_komdigi_links.json
"""
from __future__ import annotations

import asyncio
import json
import re

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from crawl.core.settings import DB_DIR
from crawl.core.schemas import KOMDIGI_LINKS_SCHEMA
from crawl.core.utils import setup_logging

logger = setup_logging(__name__)

OUTPUT_LINKS_FILE = DB_DIR / "siaran_pers_komdigi_links.json"


async def main() -> None:
    browser_config = BrowserConfig(headless=True, verbose=False)
    session_id = "komdigi_session"
    all_links: list[dict] = []

    async with AsyncWebCrawler(config=browser_config) as crawler:
        url = "https://www.komdigi.go.id/berita/siaran-pers"
        page_num = 1
        max_pages = 385

        while page_num <= max_pages:
            logger.info("--- Scraping Page %d ---", page_num)

            if page_num == 1:
                config = CrawlerRunConfig(
                    extraction_strategy=JsonCssExtractionStrategy(KOMDIGI_LINKS_SCHEMA),
                    cache_mode=CacheMode.BYPASS,
                    session_id=session_id,
                    wait_for="css:a.text-base.line-clamp-2",
                )
            else:
                js_click_next = """
                const svgNext = document.querySelector('svg.chevron-right_icon');
                if (svgNext) {
                    const button = svgNext.closest('button');
                    if (button && !svgNext.classList.contains('text-netral-gray-03')) {
                        button.click();
                    }
                }
                """
                config = CrawlerRunConfig(
                    extraction_strategy=JsonCssExtractionStrategy(KOMDIGI_LINKS_SCHEMA),
                    cache_mode=CacheMode.BYPASS,
                    session_id=session_id,
                    js_code=js_click_next,
                    js_only=True,
                    wait_for="css:a.text-base.line-clamp-2",
                )

            result = await crawler.arun(url=url, config=config)
            if not result.success:
                logger.error("Failed page %d: %s", page_num, result.error_message)
                break

            try:
                data = json.loads(result.extracted_content or "[]")
                if not data:
                    logger.warning("No links on page %d. Ending.", page_num)
                    break
                logger.info("Found %d items on page %d.", len(data), page_num)
                all_links.extend(data)
            except Exception as exc:
                logger.error("Error parsing page %d: %s", page_num, exc)
                break

            if re.search(r"chevron-right_icon[^>]*text-netral-gray-03", result.html or "") or \
               re.search(r"text-netral-gray-03[^>]*chevron-right_icon", result.html or ""):
                logger.info("Reached last page (Next disabled).")
                break

            try:
                page_num = int(all_links[-1].get("page", page_num)) + 1
            except ValueError:
                page_num += 1

            await asyncio.sleep(3)

    # -----------------------------------------------------------------------
    # Deduplicate and flatten (fixes original bug in remove_duplicates script)
    # -----------------------------------------------------------------------
    flat_items: list[dict] = []
    seen_links: set[str] = set()

    for page_data in all_links:
        items = page_data.get("news_items", [])
        for item in items:
            link = item.get("link", "")
            if link and link not in seen_links:
                seen_links.add(link)
                flat_items.append(item)

    logger.info("Scraping complete! Unique links collected: %d", len(flat_items))

    OUTPUT_LINKS_FILE.write_text(
        json.dumps(flat_items, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Saved to %s", OUTPUT_LINKS_FILE)


if __name__ == "__main__":
    asyncio.run(main())
