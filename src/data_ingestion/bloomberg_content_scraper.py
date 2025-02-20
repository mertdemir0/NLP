"""Content scraper for Bloomberg articles."""
import logging
import asyncio
from datetime import datetime
from typing import List, Dict
from playwright.async_api import async_playwright, TimeoutError
from .database import init_db, BloombergArticle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BloombergContentScraper:
    """Scraper for extracting content from Bloomberg articles."""
    
    def __init__(self):
        """Initialize the content scraper."""
        self.db_session = init_db()
    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'db_session'):
            self.db_session.close()
    
    async def extract_article_content(self, page, url: str) -> str:
        """Extract content from a Bloomberg article."""
        try:
            # Navigate to article with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    break
                except TimeoutError:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Timeout on URL {url}, attempt {attempt + 1}/{max_retries}")
                    await asyncio.sleep(2)
            
            # Wait for and get the main content
            content = ""
            
            # Try multiple selectors for Bloomberg content
            selectors = [
                'div.body-content',  # Main article content
                'div.body-copy',     # Alternative content container
                'div[data-component="body-content"]',  # Component-based layout
                'article',           # Generic article container
                'div.article-body'   # Another common container
            ]
            
            for selector in selectors:
                try:
                    content_elem = await page.wait_for_selector(selector, timeout=5000)
                    if content_elem:
                        # Get all paragraphs
                        paragraphs = await content_elem.query_selector_all('p')
                        content_parts = []
                        
                        for p in paragraphs:
                            text = await p.text_content()
                            if text.strip():
                                content_parts.append(text.strip())
                        
                        content = '\n\n'.join(content_parts)
                        if content.strip():
                            break
                except:
                    continue
            
            if not content.strip():
                # Fallback: try to get any paragraph content
                paragraphs = await page.query_selector_all('p')
                content_parts = []
                for p in paragraphs:
                    text = await p.text_content()
                    if text.strip():
                        content_parts.append(text.strip())
                content = '\n\n'.join(content_parts)
            
            return content.strip() if content else "Content not available"
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return "Error extracting content"
    
    async def process_articles(self) -> None:
        """Process articles to extract their content."""
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                ]
            )
            
            try:
                # Create context with more performance optimizations
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    java_script_enabled=True,
                    bypass_csp=True,
                    ignore_https_errors=True
                )
                
                # Get articles without content
                articles = self.db_session.query(BloombergArticle).filter(
                    BloombergArticle.content == ""
                ).all()
                
                logger.info(f"Found {len(articles)} articles to process")
                
                # Create a pool of pages
                page_count = min(5, len(articles))  # Use up to 5 pages concurrently
                pages = []
                for _ in range(page_count):
                    page = await context.new_page()
                    pages.append(page)
                
                # Process articles using the page pool
                current_page = 0
                updated_count = 0
                
                for article in articles:
                    try:
                        logger.info(f"Processing article: {article.title}")
                        
                        # Use the next available page
                        page = pages[current_page]
                        current_page = (current_page + 1) % len(pages)
                        
                        # Get content and update existing article
                        content = await self.extract_article_content(page, article.url)
                        if content and content != "Content not available" and content != "Error extracting content":
                            article.content = content
                            updated_count += 1
                        
                        # Commit after each article
                        self.db_session.commit()
                        
                        # Add delay between articles
                        await asyncio.sleep(2)
                            
                    except Exception as e:
                        self.db_session.rollback()
                        logger.error(f"Error processing article {article.title}: {str(e)}")
                        continue
                
                logger.info(f"Updated content for {updated_count} articles")
                
            finally:
                # Clean up all pages
                for page in pages:
                    await page.close()
                await context.close()
                await browser.close()
    
    def run(self):
        """Run the content scraper."""
        asyncio.run(self.process_articles())
