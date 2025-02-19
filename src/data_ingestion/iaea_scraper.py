"""IAEA News Scraper for collecting articles from IAEA website."""
import logging
from datetime import datetime
import time
import os
import re
from typing import List, Dict, Tuple
from playwright.sync_api import sync_playwright
from multiprocessing import Pool, Manager
from .database import init_db, RawArticle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_page_worker(args: Tuple[int, str]) -> List[Dict]:
    """Worker function to process a single page."""
    page_num, base_url = args
    articles = []
    page_url = f"{base_url}/news?topics=All&type=All&keywords=&page={page_num}"
    
    logger.info(f"Processing page {page_num}: {page_url}")
    
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = context.new_page()
            
            # Navigate to the page
            page.goto(page_url)
            # Wait for articles container to load
            page.wait_for_selector('div.row div.grid', timeout=10000)
            
            # Get all article grid elements
            article_elements = page.locator('div.row > div.col-xs-12').all()
            logger.info(f"Found {len(article_elements)} article elements on page {page_num}")
            
            for article in article_elements:
                try:
                    # Get article type
                    type_elem = article.locator('div.content-type-label-wrapper').first
                    article_type = type_elem.text_content().strip() if type_elem else "Unknown"
                    
                    # Get date
                    date_elem = article.locator('span.dateline-published').first
                    date = date_elem.text_content().strip() if date_elem else ""
                    
                    # Get title and link
                    title_elem = article.locator('h4 a').first
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
                        href = f"{base_url}{href}"
                    
                    logger.info(f"Processing {article_type}: {title}")
                    
                    # Navigate to the article page
                    page.goto(href)
                    page.wait_for_selector('article', timeout=10000)
                    
                    # Get content based on article type
                    content = ""
                    content_selectors = [
                        'div.field--name-body',
                        'div.field--type-text-with-summary',
                        'div.news-story-text',
                        'article div.text'
                    ]
                    
                    for selector in content_selectors:
                        content_elem = page.locator(selector).first
                        if content_elem:
                            content = content_elem.text_content().strip()
                            if content:
                                break
                    
                    # Get topics
                    topics = []
                    topic_elements = page.locator('div.field--name-field-topics a').all()
                    for topic in topic_elements:
                        topic_text = topic.text_content().strip()
                        if topic_text:
                            topics.append(topic_text)
                    
                    article_data = {
                        'title': title,
                        'content': content if content else "Content not available",
                        'url': href,
                        'date': date,
                        'topics': topics,
                        'source': 'IAEA',
                        'type': article_type
                    }
                    
                    articles.append(article_data)
                    logger.info(f"Successfully extracted {article_type}: {title}")
                    
                    # Go back to the listing page
                    page.goto(page_url)
                    page.wait_for_selector('div.row div.grid', timeout=10000)
                    
                except Exception as e:
                    logger.error(f"Error processing article: {str(e)}")
                    # Go back to the listing page
                    page.goto(page_url)
                    page.wait_for_selector('div.row div.grid', timeout=10000)
                    continue
                    
            # Clean up
            page.close()
            context.close()
            browser.close()
            
    except Exception as e:
        logger.error(f"Error processing page {page_num}: {str(e)}")
    
    logger.info(f"Found {len(articles)} articles on page {page_num}")
    return articles

class IAEAScraper:
    """Scraper for IAEA news articles."""
    
    def __init__(self, max_workers: int = 4):
        """Initialize the IAEA scraper."""
        self.max_workers = max_workers
        self.base_url = "https://www.iaea.org"
        
        # Initialize database
        self.db_session = init_db()
    
    def scrape_articles(self, start_page: int = 0, end_page: int = 691) -> List[Dict]:
        """Scrape IAEA articles from the specified page range using multiple processes."""
        all_articles = []
        
        try:
            # Create a pool of workers
            with Pool(processes=self.max_workers) as pool:
                # Create list of page numbers and base URLs
                pages = [(page, self.base_url) for page in range(start_page, end_page + 1)]
                
                # Process pages in parallel
                for articles in pool.imap_unordered(process_page_worker, pages):
                    if articles:
                        all_articles.extend(articles)
                        self._save_progress(articles)
                        
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            
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
                        type=article.get('type', 'Unknown'),
                        created_at=datetime.now()
                    )
                    self.db_session.add(db_article)
            
            self.db_session.commit()
            logger.info(f"Saved {len(articles)} articles to database")
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving to database: {str(e)}")
