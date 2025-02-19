"""IAEA News Scraper for collecting articles from IAEA website."""
import logging
from datetime import datetime
import asyncio
from typing import List, Dict, Set
from playwright.async_api import async_playwright, TimeoutError
from sqlalchemy.orm import Session
from .database import init_db, RawArticle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IAEAScraper:
    """Scraper for IAEA news articles."""
    
    def __init__(self, chunk_size: int = 5):
        """Initialize the IAEA scraper."""
        self.base_url = "https://www.iaea.org"
        self.db_session = init_db()
        self.chunk_size = chunk_size
        self.seen_urls = set()
        
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'db_session'):
            self.db_session.close()
    
    def get_existing_urls(self) -> Set[str]:
        """Get all existing URLs from the database."""
        try:
            urls = {url[0] for url in self.db_session.query(RawArticle.url).all()}
            logger.info(f"Found {len(urls)} existing URLs in database")
            return urls
        except Exception as e:
            logger.error(f"Error getting existing URLs: {str(e)}")
            return set()
    
    async def scrape_page(self, context, page_num: int) -> List[Dict]:
        """Scrape articles from a single listing page."""
        articles = []
        page_url = f"{self.base_url}/news?topics=All&type=All&keywords=&page={page_num}"
        
        try:
            # Create page
            page = await context.new_page()
            
            try:
                # Go to the listing page with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await page.goto(page_url, wait_until='domcontentloaded', timeout=10000)
                        await page.wait_for_selector('div.row div.grid', timeout=10000)
                        break
                    except TimeoutError:
                        if attempt == max_retries - 1:
                            raise
                        logger.warning(f"Timeout on page {page_num}, attempt {attempt + 1}/{max_retries}")
                        await asyncio.sleep(2)
                
                # Get all article elements
                article_elements = await page.query_selector_all('div.row > div.col-xs-12')
                logger.info(f"Found {len(article_elements)} articles on page {page_num}")
                
                # Process each article
                for article_elem in article_elements:
                    try:
                        # Get article type
                        type_elem = await article_elem.query_selector('div.content-type-label-wrapper')
                        article_type = await type_elem.text_content() if type_elem else "Unknown"
                        
                        # Get date
                        date_elem = await article_elem.query_selector('span.dateline-published')
                        date = await date_elem.text_content() if date_elem else ""
                        
                        # Get title and URL
                        title_elem = await article_elem.query_selector('h4 a')
                        if title_elem:
                            title = await title_elem.text_content()
                            href = await title_elem.get_attribute('href')
                            
                            if href:
                                if not href.startswith('http'):
                                    href = f"{self.base_url}{href}"
                                
                                # Skip if URL already seen
                                if href in self.seen_urls:
                                    continue
                                
                                self.seen_urls.add(href)
                                
                                # Get topics
                                topics = []
                                topic_elements = await article_elem.query_selector_all('div.field--name-field-topics a')
                                for topic in topic_elements:
                                    topic_text = await topic.text_content()
                                    if topic_text.strip():
                                        topics.append(topic_text.strip())
                                
                                article_data = {
                                    'title': title.strip(),
                                    'url': href,
                                    'date': date.strip(),
                                    'type': article_type.strip(),
                                    'topics': topics,
                                    'source': 'IAEA'
                                }
                                
                                articles.append(article_data)
                    
                    except Exception as e:
                        logger.error(f"Error processing article element: {str(e)}")
                        continue
                
            finally:
                await page.close()
                
        except Exception as e:
            logger.error(f"Error processing page {page_num}: {str(e)}")
        
        return articles
    
    def save_articles_batch(self, articles: List[Dict], batch_size: int = 100):
        """Save articles to database in batches."""
        if not articles:
            return
            
        try:
            new_articles = []
            for article in articles:
                try:
                    db_article = RawArticle(
                        title=article['title'],
                        content="",  # We'll add content later
                        url=article['url'],
                        date=article['date'],
                        topics=article['topics'],
                        source=article['source'],
                        type=article.get('type', 'Unknown'),
                        created_at=datetime.now()
                    )
                    new_articles.append(db_article)
                except Exception as e:
                    logger.error(f"Error creating article object: {str(e)}")
                    logger.error(f"Article data: {article}")
                    continue
            
            if new_articles:
                self.db_session.bulk_save_objects(new_articles)
                self.db_session.commit()
                logger.info(f"Successfully saved {len(new_articles)} articles to database")
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving to database: {str(e)}")
            logger.error("Rolling back transaction")
    
    async def scrape_all_pages(self, start_page: int = 0, end_page: int = 691):
        """Scrape all pages of IAEA articles."""
        total_articles = []
        total_pages = end_page - start_page + 1
        
        # Load existing URLs to avoid duplicates
        self.seen_urls = self.get_existing_urls()
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                # Create persistent context
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    java_script_enabled=True
                )
                
                # Process pages in chunks
                for chunk_start in range(start_page, end_page + 1, self.chunk_size):
                    chunk_end = min(chunk_start + self.chunk_size, end_page + 1)
                    chunk_num = (chunk_start - start_page) // self.chunk_size + 1
                    total_chunks = (total_pages + self.chunk_size - 1) // self.chunk_size
                    
                    logger.info(f"Processing chunk {chunk_num}/{total_chunks} (pages {chunk_start}-{chunk_end-1})")
                    
                    # Create tasks for chunk
                    tasks = [self.scrape_page(context, page_num) for page_num in range(chunk_start, chunk_end)]
                    chunk_results = await asyncio.gather(*tasks)
                    
                    # Process results
                    chunk_articles = []
                    for result in chunk_results:
                        chunk_articles.extend(result)
                    
                    # Save chunk results
                    if chunk_articles:
                        self.save_articles_batch(chunk_articles)
                        total_articles.extend(chunk_articles)
                        logger.info(f"Progress: {len(total_articles)} articles collected ({chunk_num / total_chunks * 100:.1f}%)")
                    
                    # Small delay between chunks
                    await asyncio.sleep(1)
                
            finally:
                await context.close()
                await browser.close()
        
        return total_articles
    
    def scrape_articles(self, start_page: int = 0, end_page: int = 691):
        """Scrape IAEA articles using async Playwright."""
        try:
            return asyncio.run(self.scrape_all_pages(start_page, end_page))
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            return []
