"""
crawl/peraturan_go_id_all.py
Step 2: Crawl detail pages for all regulations, read URLs from SQLite rekapitulasi.

Changes from original:
- Reads rekap from SQLite instead of JSON files
- Writes results to SQLite regulations table (upsert — reruns are safe)
- Uses asyncio.Semaphore to bound concurrency (prevents rate-limiting)
- Schema imported from core/schemas.py
- Bare except replaced with proper logging
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path for direct execution
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, JsonCssExtractionStrategy

from crawl.core.settings import PERATURAN_CONFIG, BASE_URL_PERATURAN
from crawl.core.schemas import PERATURAN_DETAIL_SCHEMA
from crawl.core.database import get_db, get_rekapitulasi, upsert_regulations
from crawl.core.utils import setup_logging, normalise_regulation

logger = setup_logging(__name__)

BATCH_SIZE = 10          # URLs per arun_many call
MAX_CONCURRENT = 5       # Hard cap on concurrent browser pages


async def crawl_regulation_type(
    crawler: AsyncWebCrawler,
    jenis: str,
    rekap_rows: list,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    """Crawl all detail pages for one regulation type. Returns normalised rows."""
    # Build URL list from rekap data
    urls: list[str] = []
    for row in rekap_rows:
        tahun = row["tahun"]
        jumlah = row["jumlah_peraturan"] or 0
        for nomor in range(1, jumlah + 1):
            urls.append(f"{BASE_URL_PERATURAN}/id/{jenis}-no-{nomor}-tahun-{tahun}")

    logger.info("[%s] Total URLs to crawl: %d", jenis, len(urls))

    extraction_strategy = JsonCssExtractionStrategy(PERATURAN_DETAIL_SCHEMA)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        extraction_strategy=extraction_strategy,
    )

    all_rows: list[dict] = []

    for batch_start in range(0, len(urls), BATCH_SIZE):
        batch = urls[batch_start : batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(urls) + BATCH_SIZE - 1) // BATCH_SIZE
        logger.info("[%s] Batch %d/%d (%d URLs)…", jenis, batch_num, total_batches, len(batch))

        async with semaphore:
            results = await crawler.arun_many(batch, config=run_config)

        for result in results:
            if not result.success:
                logger.warning("[%s] Failed: %s — %s", jenis, result.url, result.error_message)
                continue
            try:
                data = json.loads(result.extracted_content or "[]")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and any(item.values()):
                        all_rows.append(normalise_regulation(item, jenis))
            except json.JSONDecodeError as exc:
                logger.error("[%s] JSON decode error for %s: %s", jenis, result.url, exc)

    return all_rows


async def main() -> None:
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async with AsyncWebCrawler() as crawler:
        async with get_db() as conn:
            for jenis in PERATURAN_CONFIG:
                rekap_rows = await get_rekapitulasi(conn, jenis)
                if not rekap_rows:
                    logger.warning("[%s] No rekapitulasi data in DB. Run rekapitulasi script first.", jenis)
                    continue

                rows = await crawl_regulation_type(crawler, jenis, rekap_rows, semaphore)
                if rows:
                    count = await upsert_regulations(conn, rows)
                    logger.info("[%s] Upserted %d regulation rows into DB", jenis, count)
                else:
                    logger.warning("[%s] No data scraped.", jenis)


if __name__ == "__main__":
    asyncio.run(main())
