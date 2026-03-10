"""
crawl/siaran_pers_komdigi.py
Scrape full content from Komdigi using deduplicated links.

Changes from original:
- Reads input links from DB_DIR
- Writes directly to SQLite instead of JSON file
- Concurrency bounded via Semaphore
- Imported schemas from core
"""
from __future__ import annotations

import asyncio
import json

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from crawl.core.settings import DB_DIR
from crawl.core.schemas import KOMDIGI_DETAIL_SCHEMA
from crawl.core.database import get_db, upsert_siaran_pers
from crawl.core.utils import setup_logging, ensure_absolute_url

logger = setup_logging(__name__)

INPUT_LINKS_FILE = DB_DIR / "siaran_pers_komdigi_links.json"
BASE_URL = "https://www.komdigi.go.id"
MAX_CONCURRENT = 3


async def crawl_item(
    crawler: AsyncWebCrawler,
    semaphore: asyncio.Semaphore,
    item: dict,
    idx: int,
    total: int,
) -> dict | None:
    async with semaphore:
        url = ensure_absolute_url(item["link"], BASE_URL)
        logger.info("[Komdigi] [%d/%d] Crawling: %s", idx, total, url)

        run_config = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(KOMDIGI_DETAIL_SCHEMA),
            cache_mode=CacheMode.BYPASS,
            wait_for="css:section#section_text_body",
        )

        try:
            result = await crawler.arun(url=url, config=run_config)
            if not result.success:
                logger.error("[Komdigi] Failed %s: %s", url, result.error_message)
                return None

            data = json.loads(result.extracted_content or "[]")
            detail = data[0] if isinstance(data, list) and data else (data if data else {})

            return {
                "title":   item["title"],
                "link":    url,
                "source":  "Komdigi",
                "date":    str(detail.get("date", "")).strip(),
                "content": str(detail.get("text", "")).strip(),
            }
        except Exception as exc:
            logger.error("[Komdigi] Error processing %s: %s", url, exc)
            return None
        finally:
            await asyncio.sleep(0.5)


async def main() -> None:
    if not INPUT_LINKS_FILE.exists():
        logger.error("Links file not found: %s", INPUT_LINKS_FILE)
        return

    news_items = json.loads(INPUT_LINKS_FILE.read_text(encoding="utf-8"))
    total = len(news_items)
    logger.info("Total items to crawl: %d", total)

    browser_config = BrowserConfig(headless=True)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        tasks = [
            crawl_item(crawler, semaphore, item, i + 1, total)
            for i, item in enumerate(news_items)
        ]
        results = await asyncio.gather(*tasks)

        valid = [r for r in results if r]

    if valid:
        async with get_db() as conn:
            count = await upsert_siaran_pers(conn, valid)
            logger.info("Upserted %d Komdigi articles to DB", count)
    else:
        logger.warning("No valid articles extracted.")


if __name__ == "__main__":
    asyncio.run(main())
