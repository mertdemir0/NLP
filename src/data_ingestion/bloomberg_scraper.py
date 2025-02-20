"""Scraper for Bloomberg articles using Google search."""
import logging
import asyncio
from datetime import datetime
from typing import List, Dict
from playwright.async_api import async_playwright, TimeoutError
from bs4 import BeautifulSoup
from .database import init_db, BloombergArticle
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BloombergScraper:
    """Scraper for Bloomberg articles from Google search."""
    
    def __init__(self):
        """Initialize the Bloomberg scraper."""
        self.db_session = init_db()
        self.base_url = "https://www.google.com/search"
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
    
    async def scrape_search_page(self, page, start_index: int = 0) -> List[Dict]:
        """Scrape a single Google search page."""
        articles = []
        
        try:
            # Construct search URL with additional parameters
            search_url = (
                f"{self.base_url}?q=site:bloomberg.com+nuclear"
                f"&start={start_index}&num=100&hl=en"
                f"&filter=0"  # Show all results, including omitted ones
            )
            
            # Configure additional headers
            await page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            })
            
            # Go to search page with longer timeout
            await page.goto(search_url, wait_until='networkidle', timeout=30000)
            
            # Add random delay between 2-5 seconds
            await asyncio.sleep(random.uniform(2, 5))
            
            # Wait for results with longer timeout and multiple selectors
            result_selectors = ['div.g', 'div[data-header-feature="0"]', 'div.rc']
            result_elem = None
            
            for selector in result_selectors:
                try:
                    result_elem = await page.wait_for_selector(selector, timeout=20000)
                    if result_elem:
                        break
                except:
                    continue
            
            if not result_elem:
                logger.error("No search results found")
                return []
            
            # Get page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Try different result container selectors
            results = []
            for selector in ['div.g', 'div[data-header-feature="0"]', 'div.rc']:
                results.extend(soup.select(selector))
            
            if not results:
                logger.warning("No results found with any selector")
                return []
            
            # Process results
            for result in results:
                try:
                    # Get title and URL with multiple possible selectors
                    title_elem = (
                        result.select_one('h3.r') or 
                        result.select_one('h3') or 
                        result.select_one('div.ellip')
                    )
                    
                    link_elem = (
                        result.select_one('a[data-ved]') or 
                        result.select_one('a[ping]') or 
                        result.select_one('a')
                    )
                    
                    if not title_elem or not link_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    url = link_elem.get('href', '')
                    
                    # Clean and verify URL
                    if 'url?q=' in url:
                        url = url.split('url?q=')[1].split('&')[0]
                    
                    # Verify it's a Bloomberg URL
                    if not url.startswith('https://www.bloomberg.com'):
                        continue
                    
                    # Skip if URL already seen
                    if url in self.seen_urls:
                        continue
                    
                    self.seen_urls.add(url)
                    
                    # Get summary with multiple possible selectors
                    summary_elem = (
                        result.select_one('div.VwiC3b') or 
                        result.select_one('div.s') or 
                        result.select_one('div[style*="line-height"]')
                    )
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""
                    
                    # Get date with multiple possible selectors
                    date_elem = (
                        result.select_one('span.MUxGbd.wuQ4Ob.WZ8Tjf') or 
                        result.select_one('span.f') or 
                        result.select_one('div.dhIWPd')
                    )
                    date = date_elem.get_text(strip=True) if date_elem else ""
                    
                    article_data = {
                        'title': title,
                        'url': url,
                        'summary': summary,
                        'date': date
                    }
                    
                    articles.append(article_data)
                    logger.info(f"Found article: {title}")
                    
                except Exception as e:
                    logger.error(f"Error processing search result: {str(e)}")
                    continue
            
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping search page {start_index}: {str(e)}")
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
                        source="Bloomberg",  # Fixed source
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
    
    async def scrape_all_results(self, max_pages: int = None):
        """Scrape Google search results for Bloomberg nuclear articles."""
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                # Load existing URLs
                self.seen_urls = self.get_existing_urls()
                
                # Create context
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                
                page = await context.new_page()
                
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
                    
                    # Scrape current page
                    articles = await self.scrape_search_page(page, start_index)
                    
                    # If no more results or error, break
                    if not articles:
                        break
                    
                    # Save articles and continue
                    self.save_articles(articles)
                    total_articles.extend(articles)
                    
                    # Move to next page
                    start_index += 100
                    page_count += 1
                    
                    # Add delay between pages
                    await asyncio.sleep(2)
                
                logger.info(f"Finished scraping {page_count} pages. Found {len(total_articles)} total articles")
                
            finally:
                await browser.close()
    
    def run(self, max_pages: int = None):
        """Run the Bloomberg scraper."""
        asyncio.run(self.scrape_all_results(max_pages))