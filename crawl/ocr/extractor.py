"""
crawl/ocr/extractor.py
Extract text from downloaded PDFs.
Tries direct text extraction first via pypdf, falls back to OCR via pytesseract if empty or garbled.
"""
from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader

try:
    import pytesseract
    from pdf2image import convert_from_path
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

from crawl.core.utils import setup_logging

logger = setup_logging(__name__)

GARBLED_CHARS_PER_PAGE_THRESHOLD = 50


async def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """
    Extracts text from a PDF file.
    1. Try pypdf text extraction (fast, works for digital PDFs).
    2. If the text seems empty or garbled, fall back to Tesseract OCR if installed.
    """
    path = Path(pdf_path)
    if not path.exists():
        logger.error("File not found: %s", path)
        return ""

    text = ""
    page_count = 0

    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n\n"
    except Exception as exc:
        logger.warning("pypdf error on %s: %s", path.name, exc)

    text = text.strip()

    # Heuristic for "empty/scanned" PDF: very few non-whitespace chars extracted per page
    # A typical page has 1000+ chars. If we average < 50, it's likely a scanned image.
    if page_count > 0:
        chars_per_page = len(text.replace(" ", "").replace("\n", "")) / page_count
    else:
        chars_per_page = 0

    if chars_per_page < GARBLED_CHARS_PER_PAGE_THRESHOLD:
        if PYTESSERACT_AVAILABLE:
            logger.info("PDF %s appears scanned (%.1f chars/page). Falling back to OCR...", path.name, chars_per_page)
            return await _extract_text_tesseract(path)
        else:
            logger.warning("PDF %s appears scanned, but pytesseract/pdf2image is not installed.", path.name)
            return text

    return text


async def _extract_text_tesseract(pdf_path: Path) -> str:
    """Run Tesseract OCR on a PDF. This reads synchronously but simulates async for the pipeline."""
    # Note: pdf2image and pytesseract are blocking, but we use them in a ThreadPool
    # indirectly if called via asyncio.to_thread in the pipeline. Here we just call them directly
    # and expect the caller to wrap us.
    text = ""
    try:
        pages = convert_from_path(str(pdf_path), dpi=200)
        for i, page in enumerate(pages, start=1):
            # 'ind' for Indonesian vocabulary if installed, otherwise 'eng'
            page_text = pytesseract.image_to_string(page, lang="ind+eng")
            text += f"--- Page {i} ---\n{page_text}\n\n"
        return text.strip()
    except Exception as exc:
        logger.error("OCR error on %s: %s", pdf_path.name, exc)
        return ""
