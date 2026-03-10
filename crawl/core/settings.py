"""
crawl/core/settings.py
Unified, validated configuration for the entire project.
All paths are anchored to the project root to be cwd-independent.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Project paths (always relative to this file, never to cwd)
# ---------------------------------------------------------------------------
_THIS_FILE   = Path(__file__).resolve()          # crawl/core/settings.py
_CRAWL_DIR   = _THIS_FILE.parent.parent          # crawl/
_PROJECT_DIR = _CRAWL_DIR.parent                 # project root

DB_DIR          = _PROJECT_DIR / "db"
DB_PATH         = DB_DIR / "aitf.db"
PDF_DOWNLOAD_DIR = _PROJECT_DIR / "pdf_downloads"

# Ensure directories exist at import time
DB_DIR.mkdir(parents=True, exist_ok=True)
PDF_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Peraturan.go.id  —  regulation types
# Key   : slug used in filenames, URL slugs, and DB jenis column
# Value : relative path for the rekapitulasi page
# ---------------------------------------------------------------------------
PERATURAN_CONFIG: dict[str, str] = {
    "uu":              "uu/rekapitulasi",
    "perppu":          "perppu/rekapitulasi",
    "pp":              "pp/rekapitulasi",
    "perpres":         "perpres/rekapitulasi",
    "penpres":         "penpres/rekapitulasi",
    "keppres":         "keppres/rekapitulasi",
    "inpres":          "inpres/rekapitulasi",
    "perbagi":         "perban/perbagi",
    "peraturan-kpk":   "perban/peraturan-kpk",
    "permenkominfo":   "permen/permenkominfo",
    "permenkomdigi":   "permen/permenkomdigi",
}

BASE_URL_PERATURAN = "https://peraturan.go.id"

# ---------------------------------------------------------------------------
# General news portals (BAPPENAS, BGN, ESDM)
# ---------------------------------------------------------------------------
GENERAL_SITES_CONFIG: dict[str, dict] = {
    "BAPPENAS": {
        "links": {
            "url_template": "https://www.bappenas.go.id/kategori-berita/207?page={page}",
            "schema": {
                "name": "BAPPENAS_LINKS",
                "baseSelector": "div.blog-posts",
                "fields": [
                    {"name": "page", "selector": "ul.pagination li.page-item.active", "type": "text"},
                    {
                        "name": "news_items",
                        "selector": "article.post.post-medium",
                        "type": "list",
                        "fields": [
                            {"name": "title", "selector": "div.post-content a.text-decoration-none", "type": "attribute", "attribute": "title"},
                            {"name": "link",  "selector": "div.post-content a.text-decoration-none", "type": "attribute", "attribute": "href"},
                        ],
                    },
                ],
            },
            "wait_for": "article.post.post-medium",
        },
        "detail": {
            "schema": {
                "name": "BAPPENAS_DETAIL",
                "baseSelector": "body",
                "fields": [
                    {"name": "date", "selector": "div.col-md-8 span",   "type": "text"},
                    {"name": "text", "selector": "div.moskie",           "type": "text"},
                ],
            },
            "wait_for": "div.moskie",
        },
    },
    "BGN": {
        "links": {
            "url_template": "https://www.bgn.go.id/news/siaran-pers/?page={page}",
            "schema": {
                "name": "BGN_LINKS",
                "baseSelector": "section.grid > div",
                "fields": [
                    {"name": "title", "selector": "a h3",  "type": "text"},
                    {"name": "link",  "selector": "a",      "type": "attribute", "attribute": "href"},
                ],
            },
            "wait_for": "section.grid h3",
            "js_code": "window.scrollTo(0, 1000);",
        },
        "detail": {
            "schema": {
                "name": "BGN_DETAIL",
                "baseSelector": "body",
                "fields": [
                    {"name": "date", "selector": "h3.text-gray-500",  "type": "text"},
                    {"name": "text", "selector": "section.prose",      "type": "text"},
                ],
            },
            "wait_for": "section.prose",
        },
    },
    "ESDM": {
        "links": {
            "url_template": "https://www.esdm.go.id/id/media-center/siaran-pers?page={page}",
            "schema": {
                "name": "ESDM_LINKS",
                "baseSelector": "div.row.list-berita",
                "fields": [
                    {"name": "page", "selector": "li.page.page-item.active a", "type": "text"},
                    {
                        "name": "news_items",
                        "selector": "div.berita-item",
                        "type": "list",
                        "fields": [
                            {"name": "title", "selector": "h4.title a", "type": "text"},
                            {"name": "link",  "selector": "h4.title a", "type": "attribute", "attribute": "href"},
                        ],
                    },
                ],
            },
            "wait_for": "div.berita-item",
        },
        "detail": {
            "schema": {
                "name": "ESDM_DETAIL",
                "baseSelector": "body",
                "fields": [
                    {"name": "date", "selector": "div.date.mb-3 small",  "type": "text"},
                    {"name": "text", "selector": "div.news-read",          "type": "text"},
                ],
            },
            "wait_for": "div.news-read",
        },
    },
}

# ---------------------------------------------------------------------------
# Scraper behaviour
# ---------------------------------------------------------------------------
SCRAPER_CONFIG: dict[str, int | float] = {
    "max_pages":              1,
    "max_consecutive_empty":  1,
    "concurrency_limit":      5,
    "polite_delay":           0.5,   # seconds
    "wait_timeout":           30_000,  # ms
    "pdf_download_semaphore": 10,
    "ocr_semaphore":          4,
}

# ---------------------------------------------------------------------------
# Backwards-compatible helpers (used by old scripts that import from config.py)
# ---------------------------------------------------------------------------
def get_rekapitulasi_filename(name: str) -> str:
    return f"peraturan_go_id_rekapitulasi_{name}.json"

def get_all_extracted_filename(name: str) -> str:
    return f"peraturan_go_id_all_{name}.json"

def get_metadata_filename(name: str) -> str:
    return f"peraturan_go_id_metadata_{name}.json"
