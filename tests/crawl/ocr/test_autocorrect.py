"""
tests/crawl/ocr/test_autocorrect.py
"""
import pytest
from crawl.ocr.autocorrect import correct_indonesian_text

def test_autocorrect_preserves_proper_nouns():
    # ALL CAPS
    assert correct_indonesian_text("DPR RI mengesahkan") == "DPR RI mengesahkan"
    assert correct_indonesian_text("KEMENKOMINFO") == "KEMENKOMINFO"
    
    # Title Case (assuming Proper Noun)
    assert correct_indonesian_text("Presiden Joko Widodo") == "Presiden Joko Widodo"
    assert correct_indonesian_text("Kementerian Komunikasi") == "Kementerian Komunikasi"

def test_autocorrect_preserves_punctuation():
    text = "Pasal 1, ayat (2): 'Ini adalah contoh.' "
    # We don't expect it to change these common words, but we do expect 
    # the punctuation and spacing to remain exactly the same.
    corrected = correct_indonesian_text(text)
    assert corrected == text

def test_autocorrect_empty():
    assert correct_indonesian_text("") == ""
    assert correct_indonesian_text("   \n  ") == "   \n  "
