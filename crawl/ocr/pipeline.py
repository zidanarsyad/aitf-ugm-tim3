"""
crawl/ocr/pipeline.py
Orchestrates the OCR process: Reads pending PDFs from SQLite, extracts text,
autocorrects, and updates the database.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to sys.path to allow running this script directly
root_dir = Path(__file__).parent.parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from crawl.core.settings import SCRAPER_CONFIG
from crawl.core.database import get_db, get_regulations_pending_ocr, update_regulation_ocr
from crawl.core.utils import setup_logging
from crawl.ocr.extractor import extract_text_from_pdf
from crawl.ocr.autocorrect import correct_indonesian_text

logger = setup_logging(__name__)


async def process_pdf(
    conn,
    semaphore: asyncio.Semaphore,
    reg_id: int,
    pdf_path: str,
) -> None:
    """Extract text and update DB for a single PDF."""
    async with semaphore:
        logger.info("Starting OCR for reg %d (%s)", reg_id, pdf_path)
        
        # CPU-bound extraction wrapped in to_thread so it doesn't block the loop
        raw_text = await asyncio.to_thread(extract_text_from_pdf, pdf_path)
        
        if not raw_text:
            # Mark as empty so we don't continually retry it
            logger.warning("No text extracted for reg %d. Marking empty.", reg_id)
            await update_regulation_ocr(conn, reg_id, "<EMPTY>", "<EMPTY>")
            return

        # CPU-bound autocorrect
        corrected_text = await asyncio.to_thread(correct_indonesian_text, raw_text)

        await update_regulation_ocr(conn, reg_id, raw_text, corrected_text)
        logger.info("Finished OCR for reg %d (extracted %d chars)", reg_id, len(corrected_text))


async def run_ocr_pipeline(jenis_filter: str | None = None) -> None:
    """Run OCR and autocorrect on all downloaded PDFs that haven't been processed yet."""
    semaphore = asyncio.Semaphore(SCRAPER_CONFIG["ocr_semaphore"])

    async with get_db() as conn:
        rows = await get_regulations_pending_ocr(conn, jenis_filter)
        logger.info("Found %d PDFs pending OCR extraction.", len(rows))

        if not rows:
            return

        tasks = []
        for row in rows:
            path = row["pdf_local_path"]
            if not path:
                continue
            tasks.append(process_pdf(conn, semaphore, row["id"], path))

        await asyncio.gather(*tasks)
        logger.info("OCR Pipeline complete!")


if __name__ == "__main__":
    asyncio.run(run_ocr_pipeline())
