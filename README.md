# 🏛️ AITF UGM Tim 3: Strategi Komunikasi

![Project Banner](assets/banner.png)

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Crawl4AI](https://img.shields.io/badge/powered%20by-crawl4ai-orange.svg)](https://github.com/unclecode/crawl4ai)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance web scraping suite designed for extracting Indonesian legal regulations and public news. Built using the powerful `crawl4ai` library for efficient, automated data extraction.

### 🔍 Sources Covered:

- **Regulations**: `peraturan.go.id` (UU, Perpres, Perppu, Penpres, Keppres, Inpres, Perda, Permen, etc.)
- **News/Press Releases**:
  - `komdigi.go.id`
  - `bappenas.go.id`
  - `bgn.go.id`
  - `esdm.go.id`

---

## 📑 Table of Contents

- [🚀 Key Features](#-key-features)
- [🛠️ Installation](#️-installation)
- [ Interactive Dashboard (Recommended)](#-interactive-dashboard-recommended)
- [📖 CLI Usage Guide](#-cli-usage-guide)
  - [1. Peraturan.go.id (Regulations)](#1-peraturangoid-regulations)
  - [2. General News (BAPPENAS, BGN, ESDM)](#2-general-news-bappenas-bgn-esdm)
  - [3. Komdigi.go.id (News)](#3-komdigigoid-news)
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

### 1. Peraturan.go.id (Regulations)

#### **Step A: Generate Rekapitulasi**

Gather metadata and counts of regulations per year.

```bash
python crawl/peraturan_go_id_rekapitulasi.py
```

#### **Step B: Scrape Detailed Data**

Use rekapitulasi data to crawl individual regulation pages.

```bash
python crawl/peraturan_go_id_all.py
```

#### **Step C: Download PDFs & Extract Metadata**

Download documents and enrich JSON with PDF metadata.

```bash
python crawl/peraturan_go_id_batch_pdf_download.py
python crawl/peraturan_go_id_pdf_metadata.py
```

---

### 2. General News (BAPPENAS, BGN, ESDM)

#### **Step A: Crawl Links**

```bash
python crawl/siaran_pers_general_links.py
```

#### **Step B: Crawl Content**

```bash
python crawl/siaran_pers_general.py
```

---

### 3. Komdigi.go.id (News)

#### **Step A: Extract Links & Remove Duplicates**

```bash
python crawl/siaran_pers_komdigi_links.py
python crawl/siaran_pers_komdigi_remove_duplicates.py
```

#### **Step B: Scrape Content**

```bash
python crawl/siaran_pers_komdigi.py
```

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
