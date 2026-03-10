"""
crawl/peraturan_go_id_rekapitulasi.py
Step 1: Crawl rekapitulasi (yearly counts) for all regulation types.

Changes from original:
- Schemas imported from core/schemas.py (DRY)
- Results written to SQLite (rekapitulasi table) + JSON backup
- Paths are cwd-independent via core/settings.py
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

from crawl.core.settings import PERATURAN_CONFIG, BASE_URL_PERATURAN, DB_DIR
from crawl.core.schemas import get_rekapitulasi_schema
from crawl.core.database import get_db, upsert_rekapitulasi
from crawl.core.utils import setup_logging, coerce_int

logger = setup_logging(__name__)


async def crawl_rekapitulasi(crawler: AsyncWebCrawler, jenis: str, path: str) -> list[dict]:
    """Crawl rekapitulasi page for a single regulation type. Returns list of rows."""
    schema = get_rekapitulasi_schema(jenis)
    url = f"{BASE_URL_PERATURAN}/{path}"
    logger.info("[%s] Crawling %s", jenis, url)

    result = await crawler.arun(
        url=url,
        config=CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            extraction_strategy=JsonCssExtractionStrategy(schema),
        ),
    )

    if not result.success:
        logger.error("[%s] Failed: %s", jenis, result.error_message)
        return []

    raw: list[dict] = json.loads(result.extracted_content or "[]")
    rows: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        rows.append({
            "jenis":            jenis,
            "tahun":            coerce_int(item.get("tahun")),
            "jumlah_peraturan": coerce_int(item.get("jumlah_peraturan")),
            "berlaku":          coerce_int(item.get("berlaku")),
            "tidak_berlaku":    coerce_int(item.get("tidak_berlaku")),
        })
    return rows


async def main() -> None:
    async with AsyncWebCrawler() as crawler:
        async with get_db() as conn:
            for jenis, path in PERATURAN_CONFIG.items():
                rows = await crawl_rekapitulasi(crawler, jenis, path)
                if not rows:
                    continue

                # Write to SQLite
                count = await upsert_rekapitulasi(conn, rows)
                logger.info("[%s] Upserted %d rekapitulasi rows into DB", jenis, count)

                # JSON backup (for reference / compatibility)
                backup_path = DB_DIR / f"peraturan_go_id_rekapitulasi_{jenis}.json"
                backup_path.write_text(
                    json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                logger.info("[%s] JSON backup saved to %s", jenis, backup_path)


if __name__ == "__main__":
    asyncio.run(main())
