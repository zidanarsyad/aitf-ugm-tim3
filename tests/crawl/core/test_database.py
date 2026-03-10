"""
tests/crawl/core/test_database.py
"""
import pytest
import aiosqlite
from crawl.core.database import (
    _DDL, get_db, upsert_regulations, get_regulations_by_type,
    update_regulation_pdf, get_regulations_pending_ocr
)

# Use in-memory SQLite for tests
@pytest.fixture
async def mem_db():
    async with aiosqlite.connect(":memory:") as conn:
        conn.row_factory = aiosqlite.Row
        await conn.executescript(_DDL)
        yield conn

@pytest.mark.asyncio
async def test_upsert_regulations(mem_db):
    rows = [{
        "jenis": "uu",
        "nomor": 1,
        "tahun": 2024,
        "judul": "Test UU 1",
        "tentang": "Testing",
        "pemrakarsa": "Kemenkumham",
        "tempat_penetapan": "Jakarta",
        "ditetapkan_tanggal": "2024-01-01",
        "pejabat_menetapkan": "Presiden",
        "status": "Berlaku",
        "dokumen_url": "http://example.com/1.pdf",
    }]
    
    count = await upsert_regulations(mem_db, rows)
    assert count == 1
    
    # Check it was inserted
    db_rows = await get_regulations_by_type(mem_db, "uu")
    assert len(db_rows) == 1
    assert db_rows[0]["judul"] == "Test UU 1"
    
    # Upsert with new title
    rows[0]["judul"] = "Test UU 1 Updated"
    await upsert_regulations(mem_db, rows)
    
    db_rows = await get_regulations_by_type(mem_db, "uu")
    assert len(db_rows) == 1
    assert db_rows[0]["judul"] == "Test UU 1 Updated"

@pytest.mark.asyncio
async def test_pdf_update_and_ocr_pending(mem_db):
    rows = [{
        "jenis": "pp",
        "nomor": 2,
        "tahun": 2024,
        "judul": "PP Test",
        "tentang": None,
        "pemrakarsa": None,
        "tempat_penetapan": None,
        "ditetapkan_tanggal": None,
        "pejabat_menetapkan": None,
        "status": None,
        "dokumen_url": None,
    }]
    await upsert_regulations(mem_db, rows)
    
    # Get ID
    db_rows = await get_regulations_by_type(mem_db, "pp")
    reg_id = db_rows[0]["id"]
    
    # No PDFs pending OCR initially
    pending = await get_regulations_pending_ocr(mem_db)
    assert len(pending) == 0
    
    # Update PDF metadata
    await update_regulation_pdf(mem_db, reg_id, "/local/path.pdf", 5, 1024)
    
    # Now it should be pending OCR
    pending = await get_regulations_pending_ocr(mem_db)
    assert len(pending) == 1
    assert pending[0]["pdf_local_path"] == "/local/path.pdf"
