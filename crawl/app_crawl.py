"""
crawl/app_crawl.py
Streamlit Dashboard for AITF UGM Tim 3
Reads from and writes to the SQLite database.
Includes 3 Tabs: Regulations, Press Releases, and OCR Pipeline.
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add project root to sys.path for direct execution
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import nest_asyncio
import streamlit as st

# Apply nest_asyncio to allow asyncio.run() within Streamlit's async event loop
nest_asyncio.apply()

# ---------------------------------------------------------------------------
# Imports from our core package
# ---------------------------------------------------------------------------
from crawl.core.settings import PERATURAN_CONFIG
from crawl.core.database import get_db, get_stats
from crawl.core.utils import setup_logging

# Fix for Windows NotImplementedError (asyncio subprocess)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


class StreamlitLogHandler(logging.Handler):
    """Custom logging handler to pipe logs into a Streamlit element."""
    def __init__(self, placeholder):
        super().__init__()
        self.placeholder = placeholder
        self.logs = []

    def emit(self, record):
        msg = self.format(record)
        self.logs.append(msg)
        if len(self.logs) > 20:
            self.logs.pop(0)
        # Update the UI
        self.placeholder.code("\n".join(self.logs))


def setup_log_capture():
    """Route all script and crawl4ai logs to the Streamlit sidebar."""
    st.sidebar.subheader("实时日志 (Real-time Logs)")
    log_placeholder = st.sidebar.empty()
    handler = StreamlitLogHandler(log_placeholder)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s", datefmt="%H:%M:%S"))
    
    # Root logger
    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    # Crawl4AI logger
    crawl_logger = logging.getLogger("crawl4ai")
    if not any(isinstance(h, StreamlitLogHandler) for h in crawl_logger.handlers):
        crawl_logger.addHandler(handler)


# ---------------------------------------------------------------------------
# UI Helpers
# ---------------------------------------------------------------------------
def run_async(coro):
    """Run an async coroutine synchronously in the Streamlit context."""
    return asyncio.run(coro)


@st.cache_data(ttl=5)
def fetch_stats():
    """Fetch DB stats with a short cache to avoid stressing SQLite on every render."""
    async def _fetch():
        async with get_db() as conn:
            return await get_stats(conn)
    return run_async(_fetch())


# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------
st.set_page_config(page_title="IndoGov Crawler", layout="wide")

st.title("🏛️ Indonesian Gov Data Crawler")
st.markdown("Automated scraping + OCR for regulations and press releases. Data stored in SQLite.")

setup_log_capture()

tab0, tab1, tab2, tab3 = st.tabs([
    "📊 Dashboard", 
    "📜 Peraturan.go.id", 
    "📰 Siaran Pers", 
    "🔍 OCR Pipeline"
])

# =========================================================================
# TAB 0: DASHBOARD
# =========================================================================
with tab0:
    st.header("Data Overview (SQLite)")
    
    try:
        stats = fetch_stats()
    except Exception as e:
        st.error(f"Failed to load database: {e}")
        stats = {}
        
    if stats:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Regulations", f"{stats.get('total_regulations', 0):,}")
        m2.metric("Press Releases", f"{stats.get('total_news', 0):,}")
        m3.metric("PDFs Downloaded", f"{stats.get('pdfs_downloaded', 0):,}")
        m4.metric("OCRs Completed", f"{stats.get('ocr_done', 0):,}")
        
        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Regulations by Type")
            reg_dict = stats.get("regulations_by_type", {})
            if reg_dict:
                st.bar_chart(reg_dict)
            else:
                st.info("No regulations yet.")
                
        with c2:
            st.subheader("News by Source")
            news_dict = stats.get("news_by_source", {})
            if news_dict:
                st.bar_chart(news_dict)
            else:
                st.info("No news yet.")


# =========================================================================
# TAB 1: PERATURAN
# =========================================================================
with tab1:
    st.header("Regulations Scraper (peraturan.go.id)")
    
    col_left, col_right = st.columns(2)
    reg_type = col_left.selectbox("Select Regulation Type", list(PERATURAN_CONFIG.keys()))
    
    from crawl.peraturan_go_id_rekapitulasi import crawl_rekapitulasi
    from crawl.peraturan_go_id_all import crawl_regulation_type
    from crawl.peraturan_go_id_batch_pdf_download import main as dl_main
    from crawl.peraturan_go_id_pdf_metadata import process_type as meta_process
    from crawl4ai import AsyncWebCrawler
    
    with col_left:
        st.subheader("Phase 1: Metadata")
        
        if st.button("Step 1: Rekapitulasi & Detail"):
            with st.status("Crawling metadata...", expanded=True) as status:
                async def run_meta():
                    async with AsyncWebCrawler() as crawler:
                        async with get_db() as conn:
                            # 1. Rekap
                            st.write(f"Crawling rekapitulasi for {reg_type}...")
                            from crawl.core.database import upsert_rekapitulasi, get_rekapitulasi, upsert_regulations
                            path = PERATURAN_CONFIG[reg_type]
                            rows = await crawl_rekapitulasi(crawler, reg_type, path)
                            await upsert_rekapitulasi(conn, rows)
                            
                            # 2. Detail
                            st.write(f"Crawling detail pages for {reg_type}...")
                            rekap_db = await get_rekapitulasi(conn, reg_type)
                            sem = asyncio.Semaphore(5)
                            details = await crawl_regulation_type(crawler, reg_type, rekap_db, sem)
                            await upsert_regulations(conn, details)
                            return len(rows), len(details)
                
                try:
                    rekap_c, detail_c = run_async(run_meta())
                    status.update(label="Complete!", state="complete")
                    st.success(f"Found {rekap_c} rekap years, scraped {detail_c} regulations.")
                except Exception as e:
                    status.update(label="Failed", state="error")
                    st.error(str(e))

    with col_right:
        st.subheader("Phase 2: Documents")
        
        if st.button("Step 2: Download PDF & Extract Meta"):
            with st.status("Processing PDFs...", expanded=True) as status:
                try:
                    st.write(f"Downloading pending PDFs for {reg_type}...")
                    run_async(dl_main(jenis_filter=reg_type))
                    
                    st.write(f"Extracting PDF metadata for {reg_type}...")
                    async def run_pdf_meta():
                        import aiohttp
                        async with aiohttp.ClientSession() as session:
                            sem = asyncio.Semaphore(5)
                            await meta_process(session, sem, reg_type)
                    run_async(run_pdf_meta())
                    
                    status.update(label="Complete!", state="complete")
                    st.success("PDF pipeline finished.")
                except Exception as e:
                    status.update(label="Failed", state="error")
                    st.error(str(e))


# =========================================================================
# TAB 2: SIARAN PERS
# =========================================================================
with tab2:
    st.header("Press Releases Scraper")
    st.info("Because the news scrapers share links files, this interface runs them end-to-end.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("General (BAPPENAS, BGN, ESDM)")
        if st.button("Run General News Pipeline"):
            with st.spinner("Crawling general news..."):
                import crawl.siaran_pers_general_links as general_links
                import crawl.siaran_pers_general as general_content
                
                run_async(general_links.main())
                run_async(general_content.main())
                st.success("General news updated!")
                
    with col2:
        st.subheader("Komdigi")
        if st.button("Run Komdigi Pipeline"):
            with st.spinner("Crawling Komdigi news..."):
                import crawl.siaran_pers_komdigi_links as komdigi_links
                import crawl.siaran_pers_komdigi as komdigi_content
                
                run_async(komdigi_links.main())
                run_async(komdigi_content.main())
                st.success("Komdigi news updated!")


# =========================================================================
# TAB 3: OCR PIPELINE
# =========================================================================
with tab3:
    st.header("OCR & Text Extraction Pipeline")
    st.markdown("""
    This pipeline reads downloaded PDFs, extracts text directly if possible, 
    falls back to **Tesseract OCR** for scanned images, and then applies 
    Indonesian **Autocorrect**.
    """)
    
    jenis_ocr = st.selectbox("Filter by Type (Optional)", ["<All>"] + list(PERATURAN_CONFIG.keys()))
    filter_val = None if jenis_ocr == "<All>" else jenis_ocr
    
    if st.button("▶️ Run OCR Extraction & Autocorrect", type="primary"):
        with st.status("Running OCR Pipeline...", expanded=True) as status:
            try:
                from crawl.ocr.pipeline import run_ocr_pipeline
                run_async(run_ocr_pipeline(jenis_filter=filter_val))
                status.update(label="OCR Complete!!", state="complete")
                st.balloons()
            except Exception as e:
                status.update(label="Failed", state="error")
                st.error(str(e))
    
    st.divider()
    st.subheader("Sample Text Preview")
    if st.button("Load Random OCR Result"):
        async def fetch_sample():
            async with get_db() as conn:
                async with conn.execute("SELECT judul, ocr_corrected_text FROM regulations WHERE ocr_corrected_text IS NOT NULL ORDER BY RANDOM() LIMIT 1") as cur:
                    return await cur.fetchone()
        
        sample = run_async(fetch_sample())
        if sample:
            st.markdown(f"**{sample['judul']}**")
            with st.expander("View Text"):
                st.text(sample['ocr_corrected_text'][:2000] + "...\n\n[TRUNCATED]")
        else:
            st.info("No OCR data found in DB yet.")

# ---------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.info("AITF UGM Team 3")
st.sidebar.write(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
