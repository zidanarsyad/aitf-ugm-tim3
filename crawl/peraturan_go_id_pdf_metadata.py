"""
crawl/peraturan_go_id_pdf_metadata.py
Step 4: Extract PDF metadata (page count, size, author, etc.) for downloaded PDFs.

Changes from original:
- parse_pdf_date() imported from core/utils.py (no duplication)
- Reads from and writes to SQLite
- Paths are cwd-independent
"""
from __future__ import annotations

import asyncio
import io
import logging
from pathlib import Path

import aiohttp
from pypdf import PdfReader

from crawl.core.settings import PERATURAN_CONFIG, BASE_URL_PERATURAN
from crawl.core.database import get_db, get_regulations_by_type, update_regulation_pdf
from crawl.core.utils import setup_logging, parse_pdf_date

logger = setup_logging(__name__)

SEMAPHORE_LIMIT = 5


async def extract_pdf_metadata(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    url: str,
) -> dict:
    """Fetch PDF from URL and extract metadata. Returns a dict with extracted info."""
    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    return {"error": f"HTTP {resp.status}"}
                content = await resp.read()

            reader = PdfReader(io.BytesIO(content))
            meta = reader.metadata or {}

            info: dict = {
                "pdf_file_size_bytes": len(content),
                "pdf_page_count":      len(reader.pages),
                "pdf_version":         reader.pdf_header,
                "author":              meta.author,
                "title":               meta.title,
                "subject":             meta.subject,
                "keywords":            meta.keywords,
                "creator":             meta.creator,
                "producer":            meta.producer,
                "creation_date":       parse_pdf_date(meta.get("/CreationDate")),
                "modification_date":   parse_pdf_date(meta.get("/ModDate")),
            }

            if reader.pages:
                page = reader.pages[0]
                w = float(page.mediabox.width)
                h = float(page.mediabox.height)
                if 590 < w < 600 and 840 < h < 850:
                    info["page_size_name"] = "A4"
                elif 610 < w < 615 and 790 < h < 795:
                    info["page_size_name"] = "Letter"

            return info
        except Exception as exc:
            return {"error": str(exc)}


async def process_type(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    jenis: str,
) -> None:
    async with get_db() as conn:
        rows = await get_regulations_by_type(conn, jenis)
        tasks = []
        for row in rows:
            url = row["dokumen_url"]
            if url and url.endswith(".pdf"):
                tasks.append((row["id"], extract_pdf_metadata(session, semaphore, url)))

        if not tasks:
            logger.info("[%s] No PDF URLs found, skipping.", jenis)
            return

        logger.info("[%s] Extracting metadata for %d PDFs…", jenis, len(tasks))
        ids, coros = zip(*tasks)
        results = await asyncio.gather(*coros)

        for reg_id, meta in zip(ids, results):
            if "error" in meta:
                logger.warning("[%s] Metadata error for reg %d: %s", jenis, reg_id, meta["error"])
                continue
            await update_regulation_pdf(
                conn,
                reg_id,
                local_path=str(row["pdf_local_path"] or ""),
                page_count=meta.get("pdf_page_count"),
                file_size=meta.get("pdf_file_size_bytes"),
            )

        logger.info("[%s] Metadata update complete.", jenis)


async def main() -> None:
    semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)
    async with aiohttp.ClientSession() as session:
        for jenis in PERATURAN_CONFIG:
            await process_type(session, semaphore, jenis)


if __name__ == "__main__":
    asyncio.run(main())
