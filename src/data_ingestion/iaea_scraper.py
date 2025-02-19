"""IAEA News Scraper for collecting articles from IAEA website."""
import logging
from datetime import datetime
import time
import os
import re
import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from .database import init_db, RawArticle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IAEAScraper:
    """Scraper for IAEA news articles."""
    
    def __init__(self, max_concurrent: int = 20):
        """Initialize the IAEA scraper."""
        self.max_concurrent = max_concurrent
        self.base_url = "https://www.iaea.org"
        self.db_session = init_db()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.pending_articles = []
        
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'db_session'):
            self.db_session.close()
            
    async def extract_article_content(self, page, href: str) -> Dict:
        """Extract content from article page."""
        try:
            await page.goto(href, wait_until='domcontentloaded', timeout=5000)
            
            # Get content
            content = ""
            for selector in ['div.field--name-body', 'div.field--type-text-with-summary', 'div.news-story-text']:
                try:
                    content_elem = await page.wait_for_selector(selector, timeout=3000)
                    if content_elem:
                        content = await content_elem.text_content()
                        if content.strip():
                            break
                except:
                    continue
            
            # Get topics
            topics = []
            try:
                topic_elements = await page.query_selector_all('div.field--name-field-topics a')
                for topic in topic_elements:
                    topic_text = await topic.text_content()
                    if topic_text.strip():
                        topics.append(topic_text.strip())
            except:
                pass
                
            return {
                'content': content.strip() if content else "Content not available",
                'topics': topics
            }
        except Exception as e:
            logger.error(f"Error extracting article content: {str(e)}")
            return {'content': "Error extracting content", 'topics': []}
            
    def save_articles_batch(self, articles: List[Dict], batch_size: int = 100):
        """Save articles to database in batches."""
        if not articles:
            return
            
        try:
            # Add articles to pending list
            self.pending_articles.extend(articles)
            
            # If we have enough articles, save them in a batch
            if len(self.pending_articles) >= batch_size:
                articles_to_save = self.pending_articles[:batch_size]
                self.pending_articles = self.pending_articles[batch_size:]
                
                # Get existing URLs in a single query
                urls = [a['url'] for a in articles_to_save]
                existing_urls = {url[0] for url in self.db_session.query(RawArticle.url).filter(RawArticle.url.in_(urls)).all()}
                
                # Prepare all new articles
                new_articles = []
                for article in articles_to_save:
                    if article['url'] not in existing_urls:
                        db_article = RawArticle(
                            title=article['title'],
                            content=article['content'],
                            url=article['url'],
                            date=article['date'],
                            topics=article['topics'],
                            source=article['source'],
                            type=article.get('type', 'Unknown'),
                            created_at=datetime.now()
                        )
                        new_articles.append(db_article)
                
                # Bulk insert new articles
                if new_articles:
                    self.db_session.bulk_save_objects(new_articles)
                    self.db_session.commit()
                    logger.info(f"Saved batch of {len(new_articles)} new articles")
                
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving to database: {str(e)}")
            
    async def process_article(self, article_page, article_element, base_url: str) -> Dict:
        """Process a single article."""
        try:
            # Extract basic data
            type_elem = await article_element.query_selector('div.content-type-label-wrapper')
            article_type = await type_elem.text_content() if type_elem else "Unknown"
            
            date_elem = await article_element.query_selector('span.dateline-published')
            date = await date_elem.text_content() if date_elem else ""
            
            title_elem = await article_element.query_selector('h4 a')
            if not title_elem:
                return None
                
            title = await title_elem.text_content()
            href = await title_elem.get_attribute('href')
            
            if not href:
                return None
            
            if not href.startswith('http'):
                href = f"{base_url}{href}"
            
            # Extract full content
            content_data = await self.extract_article_content(article_page, href)
            
            return {
                'title': title.strip(),
                'url': href,
                'date': date.strip(),
                'type': article_type.strip(),
                'source': 'IAEA',
                **content_data
            }
            
        except Exception as e:
            logger.error(f"Error processing article: {str(e)}")
            return None
    
    async def process_page(self, context, page_num: int) -> List[Dict]:
        """Process a single page of articles."""
        articles = []
        page_url = f"{self.base_url}/news?topics=All&type=All&keywords=&page={page_num}"
        
        async with self.semaphore:
            try:
                # Create pages
                listing_page = await context.new_page()
                article_page = await context.new_page()
                
                # Load listing page with shorter timeout
                await listing_page.goto(page_url, wait_until='domcontentloaded', timeout=5000)
                await listing_page.wait_for_selector('div.row div.grid', timeout=5000)
                
                # Get all articles
                article_elements = await listing_page.query_selector_all('div.row > div.col-xs-12')
                
                # Process articles concurrently in smaller batches
                batch_size = 4
                for i in range(0, len(article_elements), batch_size):
                    batch = article_elements[i:i + batch_size]
                    tasks = [self.process_article(article_page, elem, self.base_url) for elem in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Add successful results
                    articles.extend([r for r in results if r is not None and not isinstance(r, Exception)])
                    
                    # Small delay between batches
                    await asyncio.sleep(0.2)
                
                # Clean up
                await listing_page.close()
                await article_page.close()
                
            except Exception as e:
                logger.error(f"Error processing page {page_num}: {str(e)}")
            
        return articles
    
    async def _scrape(self, start_page: int = 0, end_page: int = 691):
        """Internal async scraping method."""
        total_articles = []
        total_pages = end_page - start_page + 1
        
        async with async_playwright() as playwright:
            # Launch browser with optimized settings
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials'
                ]
            )
            
            try:
                # Create persistent context
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    java_script_enabled=True,
                    bypass_csp=True
                )
                
                # Process pages in larger chunks
                chunk_size = 10
                total_chunks = (total_pages + chunk_size - 1) // chunk_size
                
                for chunk_num, i in enumerate(range(start_page, end_page + 1, chunk_size)):
                    chunk_end = min(i + chunk_size, end_page + 1)
                    logger.info(f"Processing chunk {chunk_num + 1}/{total_chunks} (pages {i}-{chunk_end-1})")
                    
                    # Create tasks for chunk
                    tasks = [self.process_page(context, page_num) for page_num in range(i, chunk_end)]
                    chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    chunk_articles = []
                    for result in chunk_results:
                        if isinstance(result, list):
                            chunk_articles.extend(result)
                    
                    # Save chunk results
                    if chunk_articles:
                        self.save_articles_batch(chunk_articles)
                        total_articles.extend(chunk_articles)
                        logger.info(f"Progress: {len(total_articles)} articles collected ({(chunk_num + 1) / total_chunks * 100:.1f}%)")
                    
                    # Smaller delay between chunks
                    await asyncio.sleep(0.5)
                
                # Save any remaining articles
                if self.pending_articles:
                    self.save_articles_batch(self.pending_articles, batch_size=1)
                
            finally:
                await context.close()
                await browser.close()
                
        return total_articles
    
    def scrape_articles(self, start_page: int = 0, end_page: int = 691):
        """Scrape IAEA articles using async Playwright."""
        try:
            return asyncio.run(self._scrape(start_page, end_page))
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            return []
