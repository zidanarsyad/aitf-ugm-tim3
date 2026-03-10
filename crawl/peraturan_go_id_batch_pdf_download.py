"""
crawl/peraturan_go_id_batch_pdf_download.py
Step 3: Download PDFs for all regulations that have a dokumen_url.

Changes from original:
- Reads PDF URLs from SQLite instead of JSON files
- asyncio.Semaphore(10) replaces unbounded gather (prevents OOM)
- Updates pdf_local_path column in SQLite after each download
- Paths are cwd-independent via core/settings.py
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import aiohttp

from crawl.core.settings import PERATURAN_CONFIG, PDF_DOWNLOAD_DIR
from crawl.core.database import get_db, get_regulations_pending_download, update_regulation_pdf
from crawl.core.utils import setup_logging

logger = setup_logging(__name__)

SEMAPHORE_LIMIT = 10  # Concurrent downloads


async def download_pdf(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    reg_id: int,
    url: str,
    dest_path: Path,
) -> tuple[int, Path | None]:
    """Download a single PDF. Returns (reg_id, local_path) or (reg_id, None) on failure."""
    if dest_path.exists():
        logger.debug("Skip (exists): %s", dest_path.name)
        return reg_id, dest_path

    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    logger.warning("HTTP %s for %s", resp.status, url)
                    return reg_id, None
                content = await resp.read()
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_bytes(content)
                logger.info("Downloaded: %s (%.1f KB)", dest_path.name, len(content) / 1024)
                return reg_id, dest_path
        except Exception as exc:
            logger.error("Error downloading %s: %s", url, exc)
            return reg_id, None


async def main(jenis_filter: str | None = None) -> None:
    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)

    async with get_db() as conn:
        rows = await get_regulations_pending_download(conn, jenis_filter)
        logger.info("PDFs pending download: %d", len(rows))

        if not rows:
            logger.info("Nothing to download.")
            return

        tasks = []
        for row in rows:
            jenis = row["jenis"]
            url = row["dokumen_url"]
            filename = Path(url.split("?")[0]).name or f"reg_{row['id']}.pdf"
            dest = PDF_DOWNLOAD_DIR / jenis / filename

            async with aiohttp.ClientSession() as _session:
                pass  # Just to validate syntax; real session below
            tasks.append((row["id"], url, dest))

        async with aiohttp.ClientSession() as session:
            coros = [
                download_pdf(session, semaphore, reg_id, url, dest)
                for reg_id, url, dest in tasks
            ]
            results = await asyncio.gather(*coros)

        # Update DB
        updated = 0
        for reg_id, local_path in results:
            if local_path:
                await update_regulation_pdf(conn, reg_id, str(local_path))
                updated += 1

        logger.info("Download complete. Updated %d/%d records.", updated, len(rows))


if __name__ == "__main__":
    asyncio.run(main())
