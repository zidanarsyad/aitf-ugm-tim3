"""
crawl/core/database.py
Async SQLite database layer using aiosqlite.
Defines schema, provides context manager, and upsert helpers.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

from crawl.core.settings import DB_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------
_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS rekapitulasi (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    jenis            TEXT    NOT NULL,
    tahun            INTEGER NOT NULL,
    jumlah_peraturan INTEGER,
    berlaku          INTEGER,
    tidak_berlaku    INTEGER,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(jenis, tahun)
);

CREATE TABLE IF NOT EXISTS regulations (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    jenis                TEXT    NOT NULL,
    nomor                INTEGER,
    tahun                INTEGER,
    judul                TEXT,
    tentang              TEXT,
    pemrakarsa           TEXT,
    tempat_penetapan     TEXT,
    ditetapkan_tanggal   TEXT,
    pejabat_menetapkan   TEXT,
    status               TEXT,
    dokumen_url          TEXT,
    pdf_local_path       TEXT,
    pdf_page_count       INTEGER,
    pdf_file_size_bytes  INTEGER,
    ocr_text             TEXT,
    ocr_corrected_text   TEXT,
    scraped_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(jenis, nomor, tahun)
);

CREATE TABLE IF NOT EXISTS siaran_pers (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source     TEXT    NOT NULL,
    title      TEXT,
    link       TEXT    UNIQUE NOT NULL,
    date       TEXT,
    content    TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_regulations_jenis       ON regulations(jenis);
CREATE INDEX IF NOT EXISTS idx_regulations_status      ON regulations(status);
CREATE INDEX IF NOT EXISTS idx_regulations_ocr_pending ON regulations(jenis) WHERE pdf_local_path IS NOT NULL AND ocr_text IS NULL;
CREATE INDEX IF NOT EXISTS idx_siaran_pers_source      ON siaran_pers(source);
CREATE INDEX IF NOT EXISTS idx_rekapitulasi_jenis      ON rekapitulasi(jenis);
"""


# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------
@asynccontextmanager
async def get_db(db_path: Path = DB_PATH) -> AsyncIterator[aiosqlite.Connection]:
    """Async context manager yielding an initialised aiosqlite connection."""
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.executescript(_DDL)
        yield conn


async def init_db(db_path: Path = DB_PATH) -> None:
    """Idempotently initialise the database schema. Safe to call multiple times."""
    async with get_db(db_path):
        pass
    logger.info("Database initialised at %s", db_path)


# ---------------------------------------------------------------------------
# Rekapitulasi helpers
# ---------------------------------------------------------------------------
async def upsert_rekapitulasi(conn: aiosqlite.Connection, rows: list[dict[str, Any]]) -> int:
    """
    Insert or replace rekapitulasi rows.
    Each row must have keys: jenis, tahun, jumlah_peraturan, berlaku, tidak_berlaku.
    Returns number of rows affected.
    """
    sql = """
        INSERT INTO rekapitulasi (jenis, tahun, jumlah_peraturan, berlaku, tidak_berlaku, updated_at)
        VALUES (:jenis, :tahun, :jumlah_peraturan, :berlaku, :tidak_berlaku, CURRENT_TIMESTAMP)
        ON CONFLICT(jenis, tahun) DO UPDATE SET
            jumlah_peraturan = excluded.jumlah_peraturan,
            berlaku          = excluded.berlaku,
            tidak_berlaku    = excluded.tidak_berlaku,
            updated_at       = CURRENT_TIMESTAMP
    """
    await conn.executemany(sql, rows)
    await conn.commit()
    return len(rows)


async def get_rekapitulasi(conn: aiosqlite.Connection, jenis: str) -> list[aiosqlite.Row]:
    async with conn.execute(
        "SELECT * FROM rekapitulasi WHERE jenis=? ORDER BY tahun", (jenis,)
    ) as cur:
        return await cur.fetchall()


# ---------------------------------------------------------------------------
# Regulation helpers
# ---------------------------------------------------------------------------
async def upsert_regulations(conn: aiosqlite.Connection, rows: list[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO regulations (
            jenis, nomor, tahun, judul, tentang, pemrakarsa,
            tempat_penetapan, ditetapkan_tanggal, pejabat_menetapkan,
            status, dokumen_url, scraped_at
        ) VALUES (
            :jenis, :nomor, :tahun, :judul, :tentang, :pemrakarsa,
            :tempat_penetapan, :ditetapkan_tanggal, :pejabat_menetapkan,
            :status, :dokumen_url, CURRENT_TIMESTAMP
        )
        ON CONFLICT(jenis, nomor, tahun) DO UPDATE SET
            judul              = excluded.judul,
            tentang            = excluded.tentang,
            pemrakarsa         = excluded.pemrakarsa,
            tempat_penetapan   = excluded.tempat_penetapan,
            ditetapkan_tanggal = excluded.ditetapkan_tanggal,
            pejabat_menetapkan = excluded.pejabat_menetapkan,
            status             = excluded.status,
            dokumen_url        = excluded.dokumen_url,
            scraped_at         = CURRENT_TIMESTAMP
    """
    await conn.executemany(sql, rows)
    await conn.commit()
    return len(rows)


async def update_regulation_pdf(
    conn: aiosqlite.Connection,
    reg_id: int,
    local_path: str,
    page_count: int | None = None,
    file_size: int | None = None,
) -> None:
    await conn.execute(
        """UPDATE regulations
           SET pdf_local_path=?, pdf_page_count=?, pdf_file_size_bytes=?
           WHERE id=?""",
        (local_path, page_count, file_size, reg_id),
    )
    await conn.commit()


async def update_regulation_ocr(
    conn: aiosqlite.Connection,
    reg_id: int,
    ocr_text: str,
    ocr_corrected_text: str,
) -> None:
    await conn.execute(
        "UPDATE regulations SET ocr_text=?, ocr_corrected_text=? WHERE id=?",
        (ocr_text, ocr_corrected_text, reg_id),
    )
    await conn.commit()


async def get_regulations_by_type(
    conn: aiosqlite.Connection, jenis: str
) -> list[aiosqlite.Row]:
    async with conn.execute(
        "SELECT * FROM regulations WHERE jenis=? ORDER BY tahun, nomor", (jenis,)
    ) as cur:
        return await cur.fetchall()


async def get_regulations_pending_ocr(
    conn: aiosqlite.Connection, jenis: str | None = None
) -> list[aiosqlite.Row]:
    """Regulations that have a local PDF but no OCR text yet."""
    if jenis:
        sql = """SELECT * FROM regulations
                 WHERE pdf_local_path IS NOT NULL AND ocr_text IS NULL AND jenis=?
                 ORDER BY jenis, tahun, nomor"""
        params = (jenis,)
    else:
        sql = """SELECT * FROM regulations
                 WHERE pdf_local_path IS NOT NULL AND ocr_text IS NULL
                 ORDER BY jenis, tahun, nomor"""
        params = ()
    async with conn.execute(sql, params) as cur:
        return await cur.fetchall()


async def get_regulations_pending_download(
    conn: aiosqlite.Connection, jenis: str | None = None
) -> list[aiosqlite.Row]:
    """Regulations that have a dokumen_url (PDF link) but haven't been downloaded."""
    base = """SELECT * FROM regulations
              WHERE dokumen_url IS NOT NULL
                AND dokumen_url LIKE '%.pdf'
                AND (pdf_local_path IS NULL OR pdf_local_path = '')"""
    if jenis:
        sql = base + " AND jenis=? ORDER BY jenis, tahun, nomor"
        params = (jenis,)
    else:
        sql = base + " ORDER BY jenis, tahun, nomor"
        params = ()
    async with conn.execute(sql, params) as cur:
        return await cur.fetchall()


# ---------------------------------------------------------------------------
# Siaran pers helpers
# ---------------------------------------------------------------------------
async def upsert_siaran_pers(conn: aiosqlite.Connection, rows: list[dict[str, Any]]) -> int:
    sql = """
        INSERT INTO siaran_pers (source, title, link, date, content, scraped_at)
        VALUES (:source, :title, :link, :date, :content, CURRENT_TIMESTAMP)
        ON CONFLICT(link) DO UPDATE SET
            title      = excluded.title,
            date       = excluded.date,
            content    = excluded.content,
            scraped_at = CURRENT_TIMESTAMP
    """
    await conn.executemany(sql, rows)
    await conn.commit()
    return len(rows)


async def get_siaran_pers_by_source(
    conn: aiosqlite.Connection, source: str
) -> list[aiosqlite.Row]:
    async with conn.execute(
        "SELECT * FROM siaran_pers WHERE source=? ORDER BY date DESC", (source,)
    ) as cur:
        return await cur.fetchall()


# ---------------------------------------------------------------------------
# Stats helper (used by dashboard)
# ---------------------------------------------------------------------------
async def get_stats(conn: aiosqlite.Connection) -> dict[str, Any]:
    stats: dict[str, Any] = {}

    async with conn.execute("SELECT jenis, COUNT(*) FROM regulations GROUP BY jenis") as cur:
        stats["regulations_by_type"] = {row[0]: row[1] for row in await cur.fetchall()}

    async with conn.execute("SELECT COUNT(*) FROM regulations") as cur:
        row = await cur.fetchone()
        stats["total_regulations"] = row[0] if row else 0

    async with conn.execute("SELECT source, COUNT(*) FROM siaran_pers GROUP BY source") as cur:
        stats["news_by_source"] = {row[0]: row[1] for row in await cur.fetchall()}

    async with conn.execute("SELECT COUNT(*) FROM siaran_pers") as cur:
        row = await cur.fetchone()
        stats["total_news"] = row[0] if row else 0

    async with conn.execute(
        "SELECT COUNT(*) FROM regulations WHERE pdf_local_path IS NOT NULL"
    ) as cur:
        row = await cur.fetchone()
        stats["pdfs_downloaded"] = row[0] if row else 0

    async with conn.execute(
        "SELECT COUNT(*) FROM regulations WHERE ocr_text IS NOT NULL"
    ) as cur:
        row = await cur.fetchone()
        stats["ocr_done"] = row[0] if row else 0

    return stats
