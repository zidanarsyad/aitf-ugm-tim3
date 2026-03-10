"""
crawl/siaran_pers_general_links.py
Scrape link lists from BAPPENAS, BGN, ESDM news portals.

Changes from original:
- Config imported from core/settings.py
- Schemas imported from core/settings.py (GENERAL_SITES_CONFIG)
- Links saved to DB_DIR/siaran_pers_general_links.json (cwd-independent)
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

# Add project root to sys.path for direct execution
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from crawl.core.settings import GENERAL_SITES_CONFIG, SCRAPER_CONFIG, DB_DIR
from crawl.core.utils import setup_logging

logger = setup_logging(__name__)

OUTPUT_LINKS_FILE = DB_DIR / "siaran_pers_general_links.json"


class GeneralLinksScraper:
    def __init__(self, crawler: AsyncWebCrawler) -> None:
        self.crawler = crawler

    async def scrape_site_links(self, site_name: str, site_config: dict) -> list[dict]:
        links_cfg   = site_config["links"]
        url_template = links_cfg["url_template"]
        schema       = links_cfg["schema"]

        all_links: list[dict] = []
        consecutive_empty = 0

        logger.info("--- Starting link crawl for %s ---", site_name)

        for page_num in range(1, SCRAPER_CONFIG["max_pages"] + 1):
            url = url_template.format(page=page_num)
            logger.info("[%s] Page %d: %s", site_name, page_num, url)

            run_config = CrawlerRunConfig(
                extraction_strategy=JsonCssExtractionStrategy(schema),
                cache_mode=CacheMode.BYPASS,
                wait_for=f"css:{links_cfg['wait_for']}",
                js_code=links_cfg.get("js_code"),
                wait_for_timeout=SCRAPER_CONFIG["wait_timeout"],
            )

            try:
                result = await self.crawler.arun(url=url, config=run_config)
                if not result.success:
                    logger.error("[%s] Page %d failed: %s", site_name, page_num, result.error_message)
                    break

                data = json.loads(result.extracted_content or "[]")
                news_items = self._extract_news_items(data)

                if not news_items:
                    logger.warning("[%s] No items on page %d.", site_name, page_num)
                    consecutive_empty += 1
                    if consecutive_empty >= SCRAPER_CONFIG["max_consecutive_empty"]:
                        break
                else:
                    consecutive_empty = 0
                    processed = self._process_items(news_items, url, site_name, page_num)
                    all_links.extend(processed)
                    logger.info("[%s] Found %d items.", site_name, len(processed))

                await asyncio.sleep(SCRAPER_CONFIG["polite_delay"])

            except Exception as exc:
                logger.error("[%s] Error on page %d: %s", site_name, page_num, exc)
                break

        return all_links

    # ------------------------------------------------------------------
    def _extract_news_items(self, data) -> list[dict]:
        if isinstance(data, list):
            if data and "title" in data[0]:
                return data
            if data and "news_items" in data[0]:
                return data[0].get("news_items", [])
        elif isinstance(data, dict):
            return data.get("news_items", [])
        return []

    def _process_items(self, items: list[dict], base_url: str, source: str, page: int) -> list[dict]:
        for item in items:
            link = item.get("link", "")
            if link and not link.startswith("http"):
                item["link"] = urljoin(base_url, link)
            item["source"] = source
            item["scraped_at_page"] = page
        return items


async def main() -> None:
    browser_config = BrowserConfig(headless=True, verbose=False)
    async with AsyncWebCrawler(config=browser_config) as crawler:
        scraper = GeneralLinksScraper(crawler)
        all_results: list[dict] = []

        for site_name, site_config in GENERAL_SITES_CONFIG.items():
            links = await scraper.scrape_site_links(site_name, site_config)
            all_results.extend(links)

        logger.info("Total links collected: %d", len(all_results))
        OUTPUT_LINKS_FILE.write_text(
            json.dumps(all_results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Saved to %s", OUTPUT_LINKS_FILE)


if __name__ == "__main__":
    asyncio.run(main())
