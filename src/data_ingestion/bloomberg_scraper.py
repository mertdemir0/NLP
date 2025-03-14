"""Scraper for Bloomberg articles using SerpAPI."""
import logging
import os
from datetime import datetime
from typing import List, Dict
from serpapi import GoogleSearch
from dotenv import load_dotenv
from .database import init_db, BloombergArticle
import time

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BloombergScraper:
    """Scraper for Bloomberg articles using SerpAPI."""
    
    def __init__(self):
        """Initialize the Bloomberg scraper."""
        self.db_session = init_db()
        self.api_key = os.getenv('SERPAPI_KEY')
        if not self.api_key:
            raise ValueError("SERPAPI_KEY environment variable is not set")
        self.seen_urls = set()
    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'db_session'):
            self.db_session.close()
    
    def get_existing_urls(self) -> set:
        """Get all existing URLs from the database."""
        try:
            urls = {url[0] for url in self.db_session.query(BloombergArticle.url).all()}
            logger.info(f"Found {len(urls)} existing URLs in database")
            return urls
        except Exception as e:
            logger.error(f"Error getting existing URLs: {str(e)}")
            return set()
    
    def fetch_search_results(self, start: int = 0) -> List[Dict]:
        """Fetch search results from SerpAPI."""
        articles = []
        
        try:
            params = {
                "api_key": self.api_key,
                "engine": "google",
                "q": 'site:bloomberg.com nuclear',
                "google_domain": "google.com",
                "gl": "us",
                "hl": "en",
                "start": start,
                "num": 100
            }
            
            search = GoogleSearch(params)
            data = search.get_dict()
            
            # Process organic results
            organic_results = data.get('organic_results', [])
            if not organic_results:
                logger.warning(f"No organic results found in API response. Response: {data}")
                return []
                
            for result in organic_results:
                try:
                    url = result.get('link', '')
                    parsed_url = urlparse(url)
                    
                    # Verify it's a Bloomberg URL
                    if parsed_url.hostname != 'www.bloomberg.com':
                        continue
                    
                    # Skip if URL already seen
                    if url in self.seen_urls:
                        continue
                    
                    self.seen_urls.add(url)
                    
                    article_data = {
                        'title': result.get('title', ''),
                        'url': url,
                        'summary': result.get('snippet', ''),
                        'date': result.get('date', '')
                    }
                    
                    articles.append(article_data)
                    logger.info(f"Found article: {article_data['title']}")
                    
                except Exception as e:
                    logger.error(f"Error processing search result: {str(e)}")
                    continue
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching search results: {str(e)}")
            return []
    
    def save_articles(self, articles: List[Dict]):
        """Save articles to database."""
        if not articles:
            return
            
        try:
            new_articles = []
            for article in articles:
                try:
                    db_article = BloombergArticle(
                        title=article['title'],
                        content="",  # Empty content for future scraping
                        url=article['url'],
                        summary=article['summary'],
                        date=article['date'],
                        source="Bloomberg",
                        created_at=datetime.now()
                    )
                    new_articles.append(db_article)
                except Exception as e:
                    logger.error(f"Error creating article object: {str(e)}")
                    continue
            
            if new_articles:
                self.db_session.bulk_save_objects(new_articles)
                self.db_session.commit()
                logger.info(f"Saved {len(new_articles)} articles to database")
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving to database: {str(e)}")
    
    def scrape_all_results(self, max_pages: int = None):
        """Scrape search results for Bloomberg nuclear articles."""
        try:
            # Load existing URLs
            self.seen_urls = self.get_existing_urls()
            
            # Process search results pages
            start_index = 0
            total_articles = []
            page_count = 0
            
            while True:
                current_page = start_index // 100 + 1
                logger.info(f"Processing search results page {current_page}")
                
                # Check if we've reached max pages
                if max_pages and current_page > max_pages:
                    logger.info(f"Reached maximum pages ({max_pages}), stopping...")
                    break
                
                # Fetch current page
                articles = self.fetch_search_results(start_index)
                
                # If no more results or error, break
                if not articles:
                    logger.warning(f"No articles found on page {current_page}, stopping...")
                    break
                
                # Save articles and continue
                self.save_articles(articles)
                total_articles.extend(articles)
                
                # Move to next page
                start_index += 100
                page_count += 1
                
                # Add delay between pages
                time.sleep(2)
            
            logger.info(f"Finished scraping {page_count} pages. Found {len(total_articles)} total articles")
            
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
    
    def run(self, max_pages: int = None):
        """Run the Bloomberg scraper."""
        self.scrape_all_results(max_pages)