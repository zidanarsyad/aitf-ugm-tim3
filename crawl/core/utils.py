"""
crawl/core/utils.py
Shared utility functions used across all scrapers and pipelines.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a named logger with a consistent format.
    Handles Windows UTF-8 output encoding automatically.
    """
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
            sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except AttributeError:
            pass  # Already reconfigured or not a text stream

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                              datefmt="%H:%M:%S")
        )
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


# ---------------------------------------------------------------------------
# PDF date parser (moved from peraturan_go_id_pdf_metadata.py)
# ---------------------------------------------------------------------------
def parse_pdf_date(date_str: str | None) -> str | None:
    """
    Parse a PDF date string (e.g. ``D:20140130155254+07'00'``) into ISO 8601.
    Returns the original string if parsing fails, or None if input is None/empty.
    """
    if not date_str:
        return None
    try:
        clean = date_str.replace("D:", "").split("+")[0].split("-")[0]
        dt = datetime.strptime(clean[:14], "%Y%m%d%H%M%S")
        return dt.isoformat()
    except Exception:
        return date_str


# ---------------------------------------------------------------------------
# Integer coercion (used by rekapitulasi post-processing)
# ---------------------------------------------------------------------------
def coerce_int(value: Any, default: int = 0) -> int:
    """Safely coerce a value to int, stripping periods (Indonesian thousands sep)."""
    if value is None:
        return default
    try:
        return int(str(value).replace(".", "").strip())
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Normalise a scraped regulation dict into DB-ready shape
# ---------------------------------------------------------------------------
def normalise_regulation(raw: dict, jenis: str) -> dict:
    """
    Given a raw dict from crawl4ai extraction and the regulation type (jenis slug),
    return a dict with keys that match the ``regulations`` DB columns.
    """
    doc_url = raw.get("dokumen_url") or raw.get("dokumen_peraturan") or ""
    # Ensure absolute URL
    if doc_url and not doc_url.startswith("http"):
        from crawl.core.settings import BASE_URL_PERATURAN
        doc_url = BASE_URL_PERATURAN + "/" + doc_url.lstrip("/")

    return {
        "jenis":              jenis,
        "nomor":              coerce_int(raw.get("nomor")) or None,
        "tahun":              coerce_int(raw.get("tahun")) or None,
        "judul":              (raw.get("judul") or "").strip() or None,
        "tentang":            (raw.get("tentang") or "").strip() or None,
        "pemrakarsa":         (raw.get("pemrakarsa") or "").strip() or None,
        "tempat_penetapan":   (raw.get("tempat_penetapan") or "").strip() or None,
        "ditetapkan_tanggal": (raw.get("ditetapkan_tanggal") or "").strip() or None,
        "pejabat_menetapkan": (raw.get("pejabat yang menetapkan") or raw.get("pejabat_menetapkan") or "").strip() or None,
        "status":             (raw.get("status") or "").strip() or None,
        "dokumen_url":        doc_url or None,
    }


# ---------------------------------------------------------------------------
# Link normalisation helpers
# ---------------------------------------------------------------------------
def ensure_absolute_url(link: str, base_url: str) -> str:
    """Return an absolute URL, joining relative links with base_url."""
    from urllib.parse import urljoin
    if not link:
        return link
    if link.startswith("http"):
        return link
    return urljoin(base_url, link)
