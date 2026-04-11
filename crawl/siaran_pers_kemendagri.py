import asyncio
import json
import os
import sys
import logging
import aiohttp
from bs4 import BeautifulSoup

from config_general import SCRAPER_CONFIG, OUTPUT_LINKS_FILE, OUTPUT_CONTENT_FILE

# Ensure UTF-8 output for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KemendagriScraper:
    def __init__(self, total_pages: int):
        self.semaphore = asyncio.Semaphore(SCRAPER_CONFIG.get("concurrency_limit", 10))
        self.source_name = "KEMENDAGRI"
        self.total_pages = total_pages
        self.success_count = 0
        self.failed_count = 0
        self.processed_count = 0
        
    async def fetch_page(self, session, page: int):
        async with self.semaphore:
            url = f"https://backend.kemendagri.go.id/api/v1/blogs/public?limit=100&page={page}"
            
            try:
                async with session.get(url, timeout=30) as response:
                    self.processed_count += 1
                    progress = f"{self.processed_count}/{self.total_pages}"
                    
                    if response.status != 200:
                        self.failed_count += 1
                        logger.error(f"[{self.source_name}] Page {page} Failed: HTTP {response.status} | Progress: {progress} | Success: {self.success_count} | Failed: {self.failed_count}")
                        return None
                    
                    data = await response.json()
                    status = data.get('status')
                    if not status:
                        self.failed_count += 1
                        logger.error(f"[{self.source_name}] Page {page} Failed: False status | Progress: {progress} | Success: {self.success_count} | Failed: {self.failed_count}")
                        return None
                        
                    blogs = data.get('data', {}).get('blogs', [])
                    results = []
                    
                    for blog in blogs:
                        post_slug = str(blog.get('post_slug', '')).strip()
                        blog_name = str(blog.get('blog_name', '')).strip()
                        blog_desc_html = str(blog.get('blog_desc', '')).strip()
                        created_at = str(blog.get('created_at', '')).strip()
                        
                        if not post_slug or not blog_name:
                            continue
                            
                        # Parse HTML text if any
                        if "<" in blog_desc_html and ">" in blog_desc_html:
                            blog_desc = BeautifulSoup(blog_desc_html, "html.parser").get_text(separator=' ', strip=True)
                        else:
                            blog_desc = blog_desc_html
                            
                        link = f"https://kemendagri.go.id/berita/{post_slug}"
                        
                        record = {
                            "title": blog_name,
                            "link": link,
                            "source": self.source_name,
                            "date": created_at,
                            "text": blog_desc
                        }
                        results.append(record)
                        
                    self.success_count += len(results)
                    logger.info(f"[{self.source_name}] Page {page} Success: Fetched {len(results)} items | Progress: {progress} | Success: {self.success_count} | Failed: {self.failed_count}")
                    return results

            except Exception as e:
                # Need to handle unassigned progress variable
                if 'progress' not in locals():
                    self.processed_count += 1
                    progress = f"{self.processed_count}/{self.total_pages}"
                self.failed_count += 1
                logger.error(f"[{self.source_name}] Page {page} Error: {str(e)} | Progress: {progress} | Success: {self.success_count} | Failed: {self.failed_count}")
                return None
            finally:
                await asyncio.sleep(SCRAPER_CONFIG.get("polite_delay", 0.5))

async def main():
    os.makedirs(os.path.dirname(OUTPUT_CONTENT_FILE), exist_ok=True)
    
    # Load existing content
    existing_content = []
    scraped_links = set()
    if os.path.exists(OUTPUT_CONTENT_FILE):
        try:
            with open(OUTPUT_CONTENT_FILE, 'r', encoding='utf-8') as f:
                content_data = json.load(f)
                if isinstance(content_data, list):
                    existing_content = content_data
                    scraped_links = {item['link'] for item in existing_content if 'link' in item}
            logger.info(f"Loaded {len(existing_content)} existing articles.")
        except Exception as e:
            logger.error(f"Could not load existing content: {e}")

    # Load existing links
    existing_links = []
    if os.path.exists(OUTPUT_LINKS_FILE):
        try:
            with open(OUTPUT_LINKS_FILE, 'r', encoding='utf-8') as f:
                links_data = json.load(f)
                if isinstance(links_data, list):
                    existing_links = links_data
        except Exception as e:
            logger.error(f"Could not load existing links: {e}")

    start_page = 1
    end_page = 91

    # Override start and end page via args if provided
    if len(sys.argv) > 1:
        try:
            start_page = int(sys.argv[1])
            if len(sys.argv) > 2:
                end_page = int(sys.argv[2])
        except ValueError:
            logger.error("Invalid start/end page provided. Using defaults.")

    pages_to_scrape = list(range(start_page, end_page + 1))
    total_pages = len(pages_to_scrape)
    logger.info(f"Scraping from Page {start_page} to {end_page}. Total pages to fetch: {total_pages}")

    if total_pages == 0:
        logger.info("No pages to scrape.")
        return

    scraper = KemendagriScraper(total_pages)
    
    async with aiohttp.ClientSession() as session:
        batch_size = 10
        for i in range(0, total_pages, batch_size):
            batch_pages = pages_to_scrape[i:i + batch_size]
            current_batch_num = i // batch_size + 1
            total_batches = (total_pages + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {current_batch_num}/{total_batches} ({len(batch_pages)} pages)")
            
            tasks = [scraper.fetch_page(session, page) for page in batch_pages]
            results = await asyncio.gather(*tasks)
            
            # Flatten results and filter None or already scraped
            valid_results = []
            for page_results in results:
                if page_results:
                    for r in page_results:
                        if r['link'] not in scraped_links:
                            valid_results.append(r)
                            scraped_links.add(r['link'])

            if valid_results:
                existing_content = valid_results + existing_content
                with open(OUTPUT_CONTENT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(existing_content, f, indent=2, ensure_ascii=False)
                
                new_links = [{"source": r['source'], "title": r['title'], "link": r['link']} for r in valid_results]
                existing_links = new_links + existing_links
                with open(OUTPUT_LINKS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(existing_links, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Batch {current_batch_num} saved. Added {len(valid_results)} new articles.")
            
            # Short break between batches
            if i + batch_size < total_pages:
                await asyncio.sleep(2)

    logger.info("Kemendagri Scraping process completed.")

if __name__ == "__main__":
    asyncio.run(main())
