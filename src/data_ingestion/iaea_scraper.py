"""IAEA News Scraper for collecting articles from IAEA website."""
import logging
from datetime import datetime
import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright
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
    
    def __init__(self):
        """Initialize the IAEA scraper."""
        self.base_url = "https://www.iaea.org"
        self.db_session = init_db()
        
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'db_session'):
            self.db_session.close()
    
    async def scrape_listing_page(self, page_url: str) -> List[Dict]:
        """Scrape articles from a single listing page."""
        articles = []
        
        async with async_playwright() as playwright:
            # Launch browser
            browser = await playwright.chromium.launch(headless=True)
            
            try:
                # Create context and page
                context = await browser.new_context()
                page = await context.new_page()
                
                # Go to the listing page
                logger.info(f"Loading page: {page_url}")
                await page.goto(page_url, wait_until='domcontentloaded')
                await page.wait_for_selector('div.row div.grid')
                
                # Get all article elements
                article_elements = await page.query_selector_all('div.row > div.col-xs-12')
                logger.info(f"Found {len(article_elements)} articles")
                
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
                            
                            if href and not href.startswith('http'):
                                href = f"{self.base_url}{href}"
                            
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
                            logger.info(f"Found article: {title.strip()}")
                    
                    except Exception as e:
                        logger.error(f"Error processing article element: {str(e)}")
                        continue
                
            finally:
                await browser.close()
        
        return articles
    
    def save_articles(self, articles: List[Dict]):
        """Save articles to database."""
        if not articles:
            return
            
        try:
            for article in articles:
                try:
                    logger.info(f"Attempting to save article: {article['title']}")
                    existing = self.db_session.query(RawArticle).filter_by(url=article['url']).first()
                    if not existing:
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
                        self.db_session.add(db_article)
                        logger.info(f"Added article to session: {article['title']}")
                except Exception as e:
                    logger.error(f"Error creating article object: {str(e)}")
                    logger.error(f"Article data: {article}")
                    continue
            
            logger.info("Committing session...")
            self.db_session.commit()
            logger.info(f"Successfully saved {len(articles)} articles to database")
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving to database: {str(e)}")
            logger.error("Rolling back transaction")
    
    def scrape_page(self, page_num: int = 0) -> List[Dict]:
        """Scrape a single page of articles."""
        page_url = f"{self.base_url}/news?topics=All&type=All&keywords=&page={page_num}"
        return asyncio.run(self.scrape_listing_page(page_url))
