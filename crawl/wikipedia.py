import asyncio
import json
import logging
import sys
import os
import datetime
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
DB_ROOT = Path(__file__).parent.parent / 'db'
INPUT_FILE = DB_ROOT / 'wikipedia_links.json'
OUTPUT_FILE = DB_ROOT / 'wikipedia.json'

# Schema for Wikipedia Article Extraction
schema = {
    "name": "WikipediaArticle",
    "baseSelector": "body",
    "fields": [
        {
            "name": "title",
            "selector": "span.mw-page-title-main",
            "type": "text"
        },
        {
            "name": "text",
            "selector": "div#mw-content-text",
            "type": "text"
        },
        {
            "name": "last_modified",
            "selector": "li#footer-info-lastmod",
            "type": "text"
        }
    ]
}

async def run_wikipedia_batch_crawler():
    if not INPUT_FILE.exists():
        logger.error(f"Input file {INPUT_FILE} does not exist. Run wikipedia_links.py first.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        links = json.load(f)

    if not links:
        logger.warning("No links found in input file.")
        return

    # Load existing data to support resumption
    existing_data = []
    scraped_urls = set()
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                # Use a set for O(1) lookup and ensure URLs are cleaned
                scraped_urls = {item.get('url').strip() for item in existing_data if item.get('url')}
            logger.info(f"Loaded {len(existing_data)} existing articles from {OUTPUT_FILE}.")
        except Exception as e:
            logger.error(f"Could not load existing output: {e}")

    # Step 1: Filter out already scraped URLs (Requested: do not crawl already crawled link)
    urls_to_scrape = [url for url in links if url.strip() not in scraped_urls]
    total_to_scrape = len(urls_to_scrape)
    total_links = len(links)
    
    if total_to_scrape == 0:
        logger.info("All links have already been scraped.")
        return

    logger.info(f"Progress: {len(scraped_urls)}/{total_links} articles already in database.")
    logger.info(f"Starting batch crawl for {total_to_scrape} remaining articles...")

    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(schema),
        cache_mode=CacheMode.BYPASS,
        wait_for="h1#firstHeading"
    )

    batch_size = 50 # Reduced batch size for better checkpoint frequency
    checkpoint_file = DB_ROOT / 'wikipedia_checkpoint.json'
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for i in range(0, total_to_scrape, batch_size):
            batch = urls_to_scrape[i:i + batch_size]
            current_batch_num = i//batch_size + 1
            total_batches = (total_to_scrape + batch_size - 1)//batch_size
            
            logger.info(f"Processing batch {current_batch_num}/{total_batches} ({len(batch)} URLs)")
            
            try:
                # arun_many doesn't always guarantee order matching the input list in all environments,
                # so we will match results based on their internal URL property.
                results = await crawler.arun_many(batch, config=run_config)
                
                success_count = 0
                for result in results:
                    url = result.url
                    if result.success:
                        try:
                            # The extracted_content is a JSON string because we used JsonCssExtractionStrategy
                            data = json.loads(result.extracted_content)
                            if isinstance(data, list) and len(data) > 0:
                                article_data = data[0]
                            else:
                                article_data = data if isinstance(data, dict) else {}
                            
                            article_data['url'] = url
                            existing_data.append(article_data)
                            scraped_urls.add(url)
                            success_count += 1
                            logger.info(f"Successfully scraped: {article_data.get('title', url)}")
                        except Exception as e:
                            logger.error(f"Error parsing result for {url}: {e}")
                    else:
                        logger.error(f"Failed to scrape {url}: {result.error_message}")

                # Step 2: Create checkpoint (Requested: also create checkpoint)
                # We save the full data to wikipedia.json safely
                temp_output = OUTPUT_FILE.with_suffix('.tmp')
                with open(temp_output, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, indent=4, ensure_ascii=False)
                
                # Atomic rename to prevent corruption if script is interrupted during write
                if os.path.exists(OUTPUT_FILE):
                    os.replace(temp_output, OUTPUT_FILE)
                else:
                    os.rename(temp_output, OUTPUT_FILE)
                
                # Save a lightweight checkpoint file for quick reference
                with open(checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "last_batch_index": i + len(batch),
                        "total_scraped": len(existing_data),
                        "last_url": batch[-1] if batch else None,
                        "timestamp": datetime.datetime.now().isoformat()
                    }, f, indent=4)
                
                logger.info(f"Batch {current_batch_num} saved. Total success in this batch: {success_count}/{len(batch)}")
                
            except Exception as e:
                logger.error(f"Error in batch processing: {e}")
                # Save whatever we have so far if possible
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, indent=4, ensure_ascii=False)
            
            # Small delay between batches to be polite
            await asyncio.sleep(2)

    logger.info(f"Batch crawl complete. Total articles saved: {len(existing_data)}")

if __name__ == "__main__":
    asyncio.run(run_wikipedia_batch_crawler())
