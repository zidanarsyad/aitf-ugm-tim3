"""
crawl/siaran_pers_general.py
Scrape full content from BAPPENAS, BGN, ESDM using links gathered previously.

Changes from original:
- Configs and schemas imported from core
- Writes directly to SQLite instead of JSON file
- Concurrency bounded by Semaphore
- Paths are cwd-independent
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from pathlib import Path

# Add project root to sys.path for direct execution
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from crawl.core.settings import GENERAL_SITES_CONFIG, SCRAPER_CONFIG, DB_DIR
from crawl.core.database import get_db, upsert_siaran_pers
from crawl.core.utils import setup_logging

logger = setup_logging(__name__)

OUTPUT_LINKS_FILE = DB_DIR / "siaran_pers_general_links.json"


class GeneralContentScraper:
    def __init__(self, crawler: AsyncWebCrawler, semaphore: asyncio.Semaphore) -> None:
        self.crawler = crawler
        self.semaphore = semaphore

    @staticmethod
    def clean_date(date_str: str, source: str) -> str:
        date_str = date_str.strip()
        if source == "BGN":
            if "•" in date_str:
                date_str = date_str.split("•")[-1]
            date_str = date_str.replace("Siaran Pers", "").strip()
        elif source == "ESDM":
            if " - " in date_str:
                date_str = date_str.split(" - ")[0].strip()
        return date_str

    async def scrape_article(self, item: dict, site_config: dict, idx: int, total: int) -> dict | None:
        async with self.semaphore:
            source = item["source"]
            url = item["link"]
            detail_cfg = site_config["detail"]

            logger.info("[%s] [%d/%d] Crawling: %s", source, idx, total, url)

            run_config = CrawlerRunConfig(
                extraction_strategy=JsonCssExtractionStrategy(detail_cfg["schema"]),
                cache_mode=CacheMode.BYPASS,
                wait_for=f"css:{detail_cfg['wait_for']}",
                wait_for_timeout=SCRAPER_CONFIG["wait_timeout"],
            )

            try:
                result = await self.crawler.arun(url=url, config=run_config)
                if not result.success:
                    logger.error("[%s] Failed %s: %s", source, url, result.error_message)
                    return None

                data = json.loads(result.extracted_content or "[]")
                detail = data[0] if isinstance(data, list) and data else (data if data else {})

                return {
                    "title":   item["title"],
                    "link":    url,
                    "source":  source,
                    "date":    self.clean_date(str(detail.get("date", "")), source),
                    "content": str(detail.get("text", "")).strip(),
                }
            except Exception as exc:
                logger.error("[%s] Error on %s: %s", source, url, exc)
                return None
            finally:
                await asyncio.sleep(SCRAPER_CONFIG["polite_delay"])


async def main() -> None:
    if not OUTPUT_LINKS_FILE.exists():
        logger.error("Links file not found: %s", OUTPUT_LINKS_FILE)
        return

    news_items = json.loads(OUTPUT_LINKS_FILE.read_text(encoding="utf-8"))
    logger.info("Articles to crawl: %d", len(news_items))

    browser_config = BrowserConfig(headless=True)
    semaphore = asyncio.Semaphore(SCRAPER_CONFIG["concurrency_limit"])

    async with AsyncWebCrawler(config=browser_config) as crawler:
        scraper = GeneralContentScraper(crawler, semaphore)
        tasks = []
        for i, item in enumerate(news_items, start=1):
            source = item.get("source")
            if source in GENERAL_SITES_CONFIG:
                tasks.append(scraper.scrape_article(item, GENERAL_SITES_CONFIG[source], i, len(news_items)))
            else:
                logger.warning("No config for source: %s", source)

        results = await asyncio.gather(*tasks)
        valid = [r for r in results if r]

    if valid:
        async with get_db() as conn:
            count = await upsert_siaran_pers(conn, valid)
            logger.info("Upserted %d articles to DB", count)
    else:
        logger.warning("No valid articles extracted.")


if __name__ == "__main__":
    asyncio.run(main())
