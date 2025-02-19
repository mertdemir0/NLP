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
        
        logger.info(f"Starting to process page {page_num}")
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
                logger.info(f"Loading page {page_num}: {page_url}")
                await listing_page.goto(page_url, wait_until='domcontentloaded')
                await listing_page.wait_for_selector('div.row div.grid', timeout=10000)
                
                # Get all articles
                article_elements = await listing_page.query_selector_all('div.row > div.col-xs-12')
                logger.info(f"Found {len(article_elements)} articles on page {page_num}")
                
                # Process articles one by one to avoid rate limiting
                for i, article_elem in enumerate(article_elements):
                    try:
                        logger.info(f"Processing article {i+1}/{len(article_elements)} on page {page_num}")
                        article = await self.process_article(article_page, article_elem, self.base_url)
                        if article:
                            articles.append(article)
                            logger.info(f"Successfully processed article: {article['title']}")
                            # Add delay between articles
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Error processing article: {str(e)}")
                        continue
                
                # Clean up
                await listing_page.close()
                await article_page.close()
                await context.close()
                
                logger.info(f"Completed processing page {page_num}, found {len(articles)} articles")
                
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
        total_articles = []
        async with async_playwright() as playwright:
            # Launch browser with optimized settings
            browser = await playwright.chromium.launch(
                headless=True,
                args=['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                # Process pages sequentially to avoid rate limiting
                for page_num in range(start_page, end_page + 1):
                    # Process page and get articles
                    page_articles = await self.process_page(browser, page_num)
                    
                    # Save articles and add to total
                    if page_articles:
                        self.save_articles(page_articles)
                        total_articles.extend(page_articles)
                        logger.info(f"Saved {len(page_articles)} articles from page {page_num}")
                    
                    # Add delay between pages
                    await asyncio.sleep(1)
                
            finally:
                await browser.close()
                
        return total_articles
    
    def scrape_articles(self, start_page: int = 0, end_page: int = 691):
        """Scrape IAEA articles using async Playwright."""
        try:
            # Run async scraping
            return asyncio.run(self._scrape(start_page, end_page))
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            return []
