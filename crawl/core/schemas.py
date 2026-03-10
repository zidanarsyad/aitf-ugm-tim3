"""
crawl/core/schemas.py
Single source of truth for all crawl4ai JsonCssExtractionStrategy schemas.
Import from here instead of redefining inline in individual scrapers.
"""

# ---------------------------------------------------------------------------
# Rekapitulasi schemas
# ---------------------------------------------------------------------------
REKAPITULASI_DEFAULT_SCHEMA: dict = {
    "name": "Rekapitulasi Peraturan",
    "baseSelector": "div.accordion_2 div.card",
    "fields": [
        {"name": "tahun",            "selector": "h5.mb-0 a",                        "type": "text"},
        {"name": "jumlah_peraturan", "selector": "div.card-body li:nth-child(1) small", "type": "text"},
        {"name": "berlaku",          "selector": "div.card-body li:nth-child(2) small", "type": "text"},
        {"name": "tidak_berlaku",    "selector": "div.card-body li:nth-child(3) small", "type": "text"},
    ],
}

REKAPITULASI_PERDA_SCHEMA: dict = {
    "name": "Rekapitulasi Perda",
    "baseSelector": "div#accordionFlushExample div.accordion-item",
    "fields": [
        {"name": "tahun",            "selector": "h2.accordion-header button",             "type": "text"},
        {"name": "jumlah_peraturan", "selector": "div.accordion-body li:nth-child(1) small", "type": "text"},
        {"name": "berlaku",          "selector": "div.accordion-body li:nth-child(2) small", "type": "text"},
        {"name": "tidak_berlaku",    "selector": "div.accordion-body li:nth-child(3) small", "type": "text"},
    ],
}


def get_rekapitulasi_schema(reg_type: str) -> dict:
    """Return the correct rekapitulasi schema for a given regulation type."""
    return REKAPITULASI_PERDA_SCHEMA if reg_type.startswith("perda") else REKAPITULASI_DEFAULT_SCHEMA


# ---------------------------------------------------------------------------
# Regulation detail schema
# ---------------------------------------------------------------------------
PERATURAN_DETAIL_SCHEMA: dict = {
    "name": "Peraturan",
    "baseSelector": "section#description",
    "fields": [
        {"name": "judul",              "selector": "div.detail_title_1",          "type": "text"},
        {"name": "jenis",              "selector": "tbody tr:nth-child(1) td",    "type": "text"},
        {"name": "pemrakarsa",         "selector": "tbody tr:nth-child(2) td",    "type": "text"},
        {"name": "nomor",              "selector": "tbody tr:nth-child(3) td",    "type": "text"},
        {"name": "tahun",              "selector": "tbody tr:nth-child(4) td",    "type": "text"},
        {"name": "tentang",            "selector": "tbody tr:nth-child(5) td",    "type": "text"},
        {"name": "tempat_penetapan",   "selector": "tbody tr:nth-child(6) td",    "type": "text"},
        {"name": "ditetapkan_tanggal", "selector": "tbody tr:nth-child(7) td",    "type": "text"},
        {"name": "pejabat_menetapkan", "selector": "tbody tr:nth-child(8) td",    "type": "text"},
        {"name": "status",             "selector": "tbody tr:nth-child(9) td",    "type": "text"},
        {
            "name":      "dokumen_url",
            "selector":  "tbody tr:nth-child(10) td a",
            "type":      "attribute",
            "attribute": "href",
        },
    ],
}


# ---------------------------------------------------------------------------
# Komdigi news schemas
# ---------------------------------------------------------------------------
KOMDIGI_LINKS_SCHEMA: dict = {
    "name": "News Links",
    "baseSelector": "body",
    "fields": [
        {"name": "page", "selector": "button.relative.px-3.py-2.text-body-l", "type": "text"},
        {
            "name":     "news_items",
            "selector": "div.flex.flex-col.gap-1",
            "type":     "list",
            "fields": [
                {"name": "title", "selector": "a.line-clamp-2", "type": "text"},
                {"name": "link",  "selector": "a.line-clamp-2", "type": "attribute", "attribute": "href"},
            ],
        },
    ],
}

KOMDIGI_DETAIL_SCHEMA: dict = {
    "name": "Siaran Pers Detail",
    "baseSelector": "body",
    "fields": [
        {"name": "date", "selector": "section.flex.mt-5 div.flex-wrap span.text-body-l:not([style])", "type": "text"},
        {"name": "text", "selector": "section#section_text_body", "type": "text"},
    ],
}
