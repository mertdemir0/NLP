"""Content scraper for nuclear-related IAEA articles."""
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Set
from playwright.async_api import async_playwright, TimeoutError
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from .database import init_db, RawArticle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Nuclear-related keywords
NUCLEAR_KEYWORDS = {
    # Nuclear Power and Technology
    'nuclear','nuclear power', 'nuclear energy', 'nuclear reactor', 'nuclear plant',
    'nuclear technology', 'nuclear fusion', 'nuclear fission', 'nuclear waste',
    'uranium', 'plutonium', 'thorium', 'enrichment', 'spent fuel',
    'small modular reactor', 'smr', 'pressurized water reactor', 'pwr',
    'boiling water reactor', 'bwr', 'nuclear fuel', 'nuclear fuel cycle',
    'nuclear power plant', 'nuclear power station', 'nuclear power system',
    'Nuclear Energy','Nuclear','Fukushima'    # Nuclear Safety and Incidents
    'chernobyl', 'fukushima', 'three mile island', 'nuclear accident',
    'nuclear safety', 'nuclear security', 'radiation leak', 'meltdown',
    'nuclear contamination', 'nuclear disaster', 'radiation exposure',
    'nuclear emergency', 'nuclear incident', 'radiation protection',
    
    # Nuclear Research and Applications
    #'nuclear medicine', 'radioisotope', 'nuclear research', 'nuclear science',
    #'nuclear physics', 'particle accelerator', 'nuclear diagnostic',
    #'nuclear imaging', 'radiotherapy', 'nuclear treatment',
    
    # Nuclear Policy and Safeguards
    #'nuclear proliferation', 'nuclear safeguard', 'nuclear treaty',
    #'nuclear weapon', 'nuclear deterrence', 'nuclear disarmament',
    #'nuclear test', 'nuclear ban', 'nuclear inspection', 'nuclear agreement',
    #'nuclear deal', 'nuclear protocol', 'nuclear verification',
    
    # Nuclear Facilities and Infrastructure
    'nuclear facility', 'nuclear site', 'nuclear storage', 'nuclear repository',
    'nuclear laboratory', 'nuclear complex', 'nuclear installation',
    'nuclear infrastructure', 'nuclear station',
    
    # Nuclear Materials and Elements
    'radioactive', 'isotope', 'nuclear material', 'fissile material',
    'heavy water', 'deuterium', 'tritium', 'nuclear fuel cycle',
    'nuclear grade', 'nuclear waste', 'radium'
}

class ContentScraper:
    """Scraper for extracting content from nuclear-related articles."""
    
    def __init__(self, chunk_size: int = 100):
        """Initialize the content scraper."""
        self.db_session = init_db()
        self.chunk_size = chunk_size
        
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'db_session'):
            self.db_session.close()
    
    def is_nuclear_related(self, title: str) -> bool:
        """Check if an article is nuclear-related based on its title."""
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in NUCLEAR_KEYWORDS)
    
    async def extract_article_content(self, page, url: str) -> str:
        """Extract content from an article page."""
        try:
            # Navigate to article with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=10000)
                    break
                except TimeoutError:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Timeout on URL {url}, attempt {attempt + 1}/{max_retries}")
                    await asyncio.sleep(2)
            
            # Wait for and get the main content
            content = ""
            try:
                # First try to get the news-story-body element
                body_elem = await page.wait_for_selector('div.news-story-body div.field-newsstory-body', timeout=5000)
                if body_elem:
                    # Get all paragraphs and list items
                    paragraphs = await body_elem.query_selector_all('p, li')
                    content_parts = []
                    
                    for p in paragraphs:
                        text = await p.text_content()
                        if text.strip():
                            content_parts.append(text.strip())
                    
                    content = '\n\n'.join(content_parts)
            except Exception as e:
                # Fallback to other selectors if news-story-body not found
                for selector in ['div.field--name-body', 'div.field--type-text-with-summary', 'div.news-story-text']:
                    try:
                        content_elem = await page.wait_for_selector(selector, timeout=3000)
                        if content_elem:
                            content = await content_elem.text_content()
                            if content.strip():
                                break
                    except:
                        continue
            
            return content.strip() if content else "Content not available"
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return "Error extracting content"

    async def process_articles_chunk(self, articles: List[RawArticle]) -> None:
        """Process a chunk of articles to extract their content."""
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
                    java_script_enabled=True,
                    bypass_csp=True,
                    ignore_https_errors=True
                )
                
                # Create a pool of pages
                page_count = min(10, len(articles))  # Use up to 10 pages concurrently
                pages = []
                for _ in range(page_count):
                    page = await context.new_page()
                    pages.append(page)
                
                # Process articles using the page pool
                current_page = 0
                updated_count = 0
                new_articles = []
                
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
                        
                        await asyncio.sleep(0.1)  # Small delay between articles
                            
                    except Exception as e:
                        logger.error(f"Error processing article {article.title}: {str(e)}")
                        continue
                
                # Commit all updates
                try:
                    self.db_session.commit()
                    logger.info(f"Updated content for {updated_count} articles")
                except Exception as e:
                    self.db_session.rollback()
                    logger.error(f"Error saving updates: {str(e)}")
                
            finally:
                # Clean up all pages
                for page in pages:
                    await page.close()
                await context.close()
                await browser.close()
    
    async def scrape_content(self):
        """Scrape content from all articles."""
        try:
            # Get all articles without content
            articles = self.db_session.query(RawArticle).filter(
                RawArticle.content == ""
            ).all()
            
            logger.info(f"Found {len(articles)} articles to process")
            
            # Process articles in chunks
            for i in range(0, len(articles), self.chunk_size):
                chunk = articles[i:i + self.chunk_size]
                chunk_num = i // self.chunk_size + 1
                total_chunks = (len(articles) + self.chunk_size - 1) // self.chunk_size
                
                logger.info(f"Processing chunk {chunk_num}/{total_chunks}")
                await self.process_articles_chunk(chunk)
                await asyncio.sleep(1)  # Delay between chunks
            
        except Exception as e:
            logger.error(f"Error during content scraping: {str(e)}")
    
    def run(self):
        """Run the content scraper."""
        asyncio.run(self.scrape_content())
