"""
tests/crawl/core/test_utils.py
"""
import pytest
from crawl.core.utils import parse_pdf_date, coerce_int, normalise_regulation


def test_parse_pdf_date():
    # Valid pypdf date string
    assert parse_pdf_date("D:20140130155254+07'00'") == "2014-01-30T15:52:54"
    assert parse_pdf_date("D:20241231235959") == "2024-12-31T23:59:59"
    
    # Invalid or garbage
    assert parse_pdf_date("Not a date") == "Not a date"
    assert parse_pdf_date("") is None
    assert parse_pdf_date(None) is None


def test_coerce_int():
    assert coerce_int("123") == 123
    assert coerce_int("1.234") == 1234
    assert coerce_int("  42  ") == 42
    assert coerce_int(42) == 42
    
    # Invalid returns default
    assert coerce_int("abc", default=0) == 0
    assert coerce_int(None, default=99) == 99


def test_normalise_regulation():
    raw = {
        "judul": "  Test Judul  ",
        "tahun": "2024",
        "nomor": "1.0",
        "dokumen_url": "/files/test.pdf"
    }
    
    # Need to patch settings so we don't depend on actual base URL if it changes,
    # but since it's hardcoded to https://peraturan.go.id, we can just test it.
    out = normalise_regulation(raw, "uu")
    
    assert out["jenis"] == "uu"
    assert out["judul"] == "Test Judul"
    assert out["tahun"] == 2024
    assert out["nomor"] == 10  # 1.0 -> stripped . -> 10
    assert out["dokumen_url"] == "https://peraturan.go.id/files/test.pdf"
    assert out["tentang"] is None
