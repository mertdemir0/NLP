"""IAEA News Scraper for collecting articles from IAEA website."""
import logging
from datetime import datetime
import time
import os
import re
from typing import List, Dict
from playwright.sync_api import sync_playwright
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
        
        # Initialize database
        self.db_session = init_db()
        
        # Initialize Playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=False  # Set to False to see what's happening
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
            self.page.goto(page_url)
            # Wait for articles to load
            self.page.wait_for_selector('div.view-content', timeout=10000)
            
            # Get the page HTML for debugging
            html = self.page.content()
            logger.info(f"Page HTML length: {len(html)}")
            
            # Try different selectors
            selectors = [
                'div.views-row article',
                'div.view-content article',
                'div.views-row',
                'article.node--type-news'
            ]
            
            article_elements = []
            for selector in selectors:
                article_elements = self.page.locator(selector).all()
                logger.info(f"Selector '{selector}' found {len(article_elements)} elements")
                if article_elements:
                    logger.info(f"Using selector: {selector}")
                    break
            
            if not article_elements:
                logger.error("No article elements found with any selector")
                return articles
            
            for article in article_elements:
                try:
                    # Debug the article HTML
                    article_html = article.evaluate('el => el.outerHTML')
                    logger.info(f"Article HTML: {article_html[:200]}...")  # First 200 chars
                    
                    # Get title and link
                    title_elem = article.locator('h2 a, h3 a').first
                    if not title_elem:
                        logger.warning("No title element found")
                        continue
                    
                    title = title_elem.text_content().strip()
                    href = title_elem.get_attribute('href')
                    
                    if not href:
                        logger.warning(f"No href found for article: {title}")
                        continue
                    
                    # Get the full URL
                    if not href.startswith('http'):
                        href = f"{self.base_url}{href}"
                    
                    # Get date
                    date = ""
                    date_elem = article.locator('div.date-display-single, time, span.date').first
                    if date_elem:
                        date = date_elem.text_content().strip()
                    
                    # Get summary
                    summary = ""
                    summary_elem = article.locator('div.field--name-body, div.field--type-text-with-summary').first
                    if summary_elem:
                        summary = summary_elem.text_content().strip()
                    
                    # Get topics
                    topics = []
                    topic_elements = article.locator('div.field--name-field-topics a, div.topics a').all()
                    for topic in topic_elements:
                        topic_text = topic.text_content().strip()
                        if topic_text:
                            topics.append(topic_text)
                    
                    article_data = {
                        'title': title,
                        'content': summary if summary else "Summary not available",
                        'url': href,
                        'date': date,
                        'topics': topics,
                        'source': 'IAEA'
                    }
                    
                    articles.append(article_data)
                    logger.info(f"Extracted article: {title}")
                    
                except Exception as e:
                    logger.error(f"Error processing article: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error processing page {page}: {str(e)}")
        
        logger.info(f"Found {len(articles)} articles on page {page}")
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
                time.sleep(2)
                
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
