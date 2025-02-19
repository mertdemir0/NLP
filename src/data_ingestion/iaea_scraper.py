"""IAEA News Scraper for collecting articles from IAEA website."""
import logging
from datetime import datetime
import time
import random
import threading
import os
import re
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Page, Browser
from .database import init_db, RawArticle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IAEAScraper:
    """Scraper for IAEA news articles."""
    
    def __init__(self, max_workers: int = 3, chunk_size: int = 5):
        """Initialize the IAEA scraper."""
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.base_url = "https://www.iaea.org"
        self.processed_urls = set()
        self.url_lock = threading.Lock()
        
        # Initialize database
        self.db_session = init_db()
        
        # Initialize Playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True
        )
        
        # Create a new context
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Create a new page
        self.page = self.context.new_page()
            
    def _process_page(self, page: int) -> List[Dict]:
        """Process a single IAEA page."""
        articles = []
        page_url = f"{self.base_url}/news?topics=All&type=All&keywords=&page={page}"
        
        logger.info(f"Processing page {page}: {page_url}")
        
        try:
            # Navigate to the page
            self.page.goto(page_url, wait_until='networkidle')
            time.sleep(2)  # Wait for any dynamic content
            
            # Get all article links
            article_elements = self.page.locator('div.views-row article').all()
            logger.info(f"Found {len(article_elements)} article elements on page {page}")
            
            for article in article_elements:
                try:
                    # Get the article link
                    link_elem = article.locator('h2 a').first
                    if not link_elem:
                        continue
                        
                    href = link_elem.get_attribute('href')
                    if not href:
                        continue
                        
                    # Get the full URL
                    if not href.startswith('http'):
                        href = f"{self.base_url}{href}"
                    
                    # Get title
                    title = link_elem.text_content().strip()
                    
                    # Get date
                    date = article.locator('div.date-display-single').text_content().strip()
                    
                    # Get summary
                    summary = article.locator('div.field--name-body').text_content().strip()
                    
                    # Get topics
                    topics = []
                    topic_elements = article.locator('div.field--name-field-topics a').all()
                    for topic in topic_elements:
                        topic_text = topic.text_content().strip()
                        if topic_text:
                            topics.append(topic_text)
                    
                    article_data = {
                        'title': title,
                        'content': summary,  # We'll use summary for now, can fetch full content later
                        'url': href,
                        'date': date,
                        'topics': topics,
                        'source': 'IAEA'
                    }
                    
                    articles.append(article_data)
                    logger.info(f"Extracted article: {title}")
                    
                except Exception as e:
                    logger.error(f"Error processing article on page {page}: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error processing page {page}: {str(e)}")
        
        return articles
    
    def scrape_articles(self, start_page: int = 0, end_page: int = 691) -> List[Dict]:
        """Scrape IAEA articles from the specified page range."""
        all_articles = []
        
        try:
            for page in range(start_page, end_page + 1):
                articles = self._process_page(page)
                if articles:
                    all_articles.extend(articles)
                    self._save_progress(articles)
                time.sleep(2)  # Be nice to the server
                
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
        finally:
            # Clean up
            if hasattr(self, 'page'):
                self.page.close()
            if hasattr(self, 'context'):
                self.context.close()
            if hasattr(self, 'browser'):
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()
            
        return all_articles
    
    def _save_progress(self, articles: List[Dict]):
        """Save scraped articles to the database."""
        if not articles:
            return
            
        try:
            for article in articles:
                # Check if article already exists
                existing = self.db_session.query(RawArticle).filter_by(url=article['url']).first()
                if not existing:
                    db_article = RawArticle(
                        title=article['title'],
                        content=article['content'],
                        url=article['url'],
                        date=article['date'],
                        topics=article['topics'],
                        source=article['source'],
                        created_at=datetime.now()
                    )
                    self.db_session.add(db_article)
            
            self.db_session.commit()
            logger.info(f"Saved {len(articles)} articles to database")
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving to database: {str(e)}")
