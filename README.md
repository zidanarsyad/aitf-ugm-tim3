# 🏛️ AITF UGM Tim 3: Strategi Komunikasi

![Project Banner](assets/banner.png)

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Crawl4AI](https://img.shields.io/badge/powered%20by-crawl4ai-orange.svg)](https://github.com/unclecode/crawl4ai)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance web scraping suite designed for extracting Indonesian legal regulations and public news. Built using the powerful `crawl4ai` library for efficient, automated data extraction.

### 🔍 Sources Covered:

- **Regulations**: `peraturan.go.id` (UU, Perpres, Perppu, Penpres, Keppres, Inpres, Perda, Permen, dll.)
- **Press Releases / News**: 20+ Ministries & Government Agencies including `dpr.go.id`, `komdigi.go.id`, `bappenas.go.id`, `esdm.go.id`, `kemensos.go.id`, `polri.go.id`, `setneg.go.id`, `bumn.go.id`, etc.
- **Context/Knowledge Base**: Wikipedia Indonesia (General government contexts)

### 📊 Dataset Links (Kaggle):

- [AITF - Peraturan Pemerintah](https://www.kaggle.com/datasets/ahmadadillaumam/aitf-peraturan-pemerintah)
- [AITF - Siaran Pers Pemerintah](https://www.kaggle.com/datasets/ahmadadillaumam/aitf-siaran-pers-pemerintah)

---

## 📑 Table of Contents

- [🚀 Key Features](#-key-features)
- [🛠️ Installation](#️-installation)
- [ Interactive Dashboard (Recommended)](#-interactive-dashboard-recommended)
- [📖 CLI Usage Guide](#-cli-usage-guide)
  - [1. Regulation Pipeline](#1-regulation-pipeline-peraturangoid)
  - [2. Siaran Pers Pipeline](#2-siaran-pers-pipeline-komdigi--general--dpr--cleaning)
  - [3. Wikipedia Pipeline](#3-wikipedia-pipeline)
- [🌐 API Server](#-api-server)
- [📂 Directory Structure](#-directory-structure)
- [📦 Data Schema](#-data-schema)
- [🛡️ License](#️-license)

---

## 🚀 Key Features

- **Multi-Source Support**: Scrapes regulations and news from 5+ Indonesian government portals.
- **Interactive UI**: Built-in Streamlit dashboard for monitoring and running crawls.
- **Smart Extraction**: Uses CSS-based JSON extraction strategies.
- **Batch Processing**: Handles multi-page navigation and batch PDF downloads.
- **Data Enrichment**: Automatically extracts metadata from downloaded PDFs.
- **Asynchronous**: Built on `asyncio` for high-speed concurrent crawling.

---

## 🛠️ Installation

### 1. Prerequisite

Ensure you have **Python 3.8+** installed.

### 2. Setup Environment

```bash
# Clone the repository
git clone https://github.com/zidanarsyad/aitf-ugm-tim3.git
cd aitf-ugm-tim3

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/scripts/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt
# Or manually:
pip install crawl4ai aiohttp streamlit nesting-asyncio pypdf
```

### 3. Initialize Crawl4AI

```bash
crawl4ai-setup
crawl4ai-doctor  # Verify the installation
```

---

## � Interactive Dashboard (Recommended)

The easiest way to use this tool is via the Streamlit dashboard:

```bash
streamlit run crawl/app_crawl.py
```

**Features in Dashboard:**

- **Stats Overview**: View total records and storage used.
- **Regulation Scraper**: Run 3-step regulation crawling (Rekap -> Details -> PDF).
- **News Scraper**: Crawl links and full content from multiple government sites simultaneously.
- **Real-time Logs**: Monitor scraping progress in the sidebar.

---

## 📖 CLI Usage Guide

The project provides an interactive pipeline orchestrator. Simply run:

```bash
python crawl/pipeline.py
# Or on Windows:
crawl\run_pipeline.bat
```

You will be presented with a menu to run one of the following pipelines:

### 1. Regulation Pipeline (`peraturan.go.id`)

Handles extraction of all Indonesian legal documents.
- `peraturan_go_id_rekapitulasi.py` - Gather metadata/counts per year.
- `peraturan_go_id_all.py` - Crawl details for general regulations.
- `peraturan_go_id_perda_links.py` & `peraturan_go_id_perda.py` - Scrape local regulations (Perda).
- `peraturan_go_id_pdf_metadata.py` & `peraturan_go_id_batch_pdf_download.py` - Download PDFs and enrich metadata.

---

### 2. Siaran Pers Pipeline (Komdigi + General + DPR + Cleaning)

Extracts news and press releases from over 20 government agency portals, then cleans the collected data.
- `siaran_pers_komdigi_links.py` & `siaran_pers_komdigi.py` - Scrape Komdigi.
- `siaran_pers_general_links.py` & `siaran_pers_general.py` - Scrape general ministries (BAPPENAS, ESDM, SETNEG, etc.).
- `siaran_pers_cleaning.py` - Cleans and standardizes the final dataset format.
> **Note**: DPR RI news scraping (`siaran_pers_dpr.py`) can be executed individually if needed.

---

### 3. Wikipedia Pipeline

Gathers contextual knowledge base from Wikipedia Indonesia.
- `wikipedia_links.py` - Discover relevant links.
- `wikipedia.py` - Scrape Wikipedia content.

---

## 🌐 API Server

The project includes a mock API server built with FastAPI implementing the communication strategy AI refinement endpoints.

```bash
# Start the API server locally
uvicorn api.main:app --reload
```

**Key API Features:**

- **Authentication**: Bearer token logic.
- **Model Listing**: `GET /v1/models`
- **Chat Completions**: `POST /v1/chat/completions` (Supports SSE streaming with `stream: true`).
- **Crawler Monitoring**: `GET /v1/crawlers/status`

---

## 📂 Directory Structure

```text
.
├── api/              # API Server
│   ├── main.py              # FastAPI application
├── crawl/            # Python scraping scripts & UI
│   ├── app_crawl.py         # Streamlit Dashboard
│   ├── config.py            # Regulation config
│   ├── config_general.py    # News portal configs (BAPPENAS, etc.)
│   ├── pipeline.py          # CLI Workflow orchestrator
│   └── ...                  # Individual scrapers
├── db/               # JSON output files (The database)
├── assets/           # Media assets for README
├── pdf_downloads/    # Downloaded PDF documents
└── README.md         # Project documentation
```

---

## 📦 Data Schema

### Regulation Schema

```json
{
  "judul": "PERATURAN PEMERINTAH NOMOR 1 TAHUN 2024",
  "jenis": "Peraturan Pemerintah",
  "nomor": 1,
  "tahun": 2024,
  "status": "Berlaku",
  "dokumen_peraturan": "https://peraturan.go.id/files/..."
}
```

### News Schema (General & Komdigi)

```json
{
  "source": "BAPPENAS",
  "title": "Menteri Bappenas Tekankan Pentingnya Transformasi Ekonomi",
  "link": "https://www.bappenas.go.id/...",
  "date": "01 Januari 2024",
  "text": "Full article content here..."
}
```

---

## 🛡️ License

Distributed under the MIT License. See `LICENSE` for more information.

---

**Developed by AITF UGM Tim 3** 🚀
