"""IAEA News Scraper for collecting articles from IAEA website."""
import logging
from datetime import datetime
import time
import os
import re
import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright
from .database import init_db, RawArticle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IAEAScraper:
    """Scraper for IAEA news articles."""
    
    def __init__(self, max_concurrent: int = 10):
        """Initialize the IAEA scraper."""
        self.max_concurrent = max_concurrent
        self.base_url = "https://www.iaea.org"
        self.db_session = init_db()
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def extract_article_content(self, page, href: str) -> Dict:
        """Extract content from article page."""
        try:
            await page.goto(href, wait_until='domcontentloaded')
            
            # Get content
            content = ""
            for selector in ['div.field--name-body', 'div.field--type-text-with-summary', 'div.news-story-text']:
                try:
                    content_elem = await page.wait_for_selector(selector, timeout=5000)
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
    
    async def process_page(self, browser, page_num: int) -> List[Dict]:
        """Process a single page of articles."""
        articles = []
        page_url = f"{self.base_url}/news?topics=All&type=All&keywords=&page={page_num}"
        
        async with self.semaphore:
            try:
                # Create context with two pages
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    java_script_enabled=True
                )
                listing_page = await context.new_page()
                article_page = await context.new_page()
                
                # Load listing page
                await listing_page.goto(page_url, wait_until='domcontentloaded')
                await listing_page.wait_for_selector('div.row div.grid', timeout=10000)
                
                # Get all articles
                article_elements = await listing_page.query_selector_all('div.row > div.col-xs-12')
                
                # Process articles concurrently
                tasks = []
                for article_elem in article_elements:
                    task = self.process_article(article_page, article_elem, self.base_url)
                    tasks.append(task)
                
                # Wait for all articles to be processed
                results = await asyncio.gather(*tasks, return_exceptions=True)
                articles = [r for r in results if r is not None and not isinstance(r, Exception)]
                
                # Clean up
                await listing_page.close()
                await article_page.close()
                await context.close()
                
            except Exception as e:
                logger.error(f"Error processing page {page_num}: {str(e)}")
            
        return articles
    
    def save_articles(self, articles: List[Dict]):
        """Save articles to database."""
        if not articles:
            return
            
        try:
            for article in articles:
                existing = self.db_session.query(RawArticle).filter_by(url=article['url']).first()
                if not existing:
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
                    self.db_session.add(db_article)
            
            self.db_session.commit()
            logger.info(f"Saved {len(articles)} articles to database")
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving to database: {str(e)}")
    
    async def _scrape(self, start_page: int = 0, end_page: int = 691):
        """Internal async scraping method."""
        async with async_playwright() as playwright:
            # Launch browser with optimized settings
            browser = await playwright.chromium.launch(
                headless=True,
                args=['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                # Create tasks for all pages
                tasks = []
                for page_num in range(start_page, end_page + 1):
                    task = self.process_page(browser, page_num)
                    tasks.append(task)
                
                # Process pages in chunks to avoid memory issues
                chunk_size = 5
                for i in range(0, len(tasks), chunk_size):
                    chunk_tasks = tasks[i:i + chunk_size]
                    chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
                    
                    # Filter out errors and flatten results
                    chunk_articles = []
                    for result in chunk_results:
                        if isinstance(result, list):
                            chunk_articles.extend(result)
                    
                    # Save chunk results
                    if chunk_articles:
                        self.save_articles(chunk_articles)
                    
                    # Small delay between chunks
                    await asyncio.sleep(1)
                
            finally:
                await browser.close()
    
    def scrape_articles(self, start_page: int = 0, end_page: int = 691):
        """Scrape IAEA articles using async Playwright."""
        try:
            # Run async scraping
            asyncio.run(self._scrape(start_page, end_page))
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
