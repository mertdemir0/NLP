"""IAEA News Scraper for collecting articles from IAEA website."""
import json
import logging
from datetime import datetime
import time
import random
import threading
import os
import re
from typing import List, Dict, Optional
from playwright.sync_api import sync_playwright, Page, Browser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IAEAScraper:
    """Scraper for IAEA news articles."""
    
    def __init__(self, max_workers: int = 3, chunk_size: int = 5):
        """Initialize the IAEA scraper.
        
        Args:
            max_workers: Maximum number of parallel workers
            chunk_size: Number of pages to process in each chunk
        """
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.base_url = "https://www.iaea.org"
        self.processed_urls = set()
        self.url_lock = threading.Lock()
        
        # Initialize Playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--window-size=1920,1080'
            ]
        )
        
        # Create a new context with random user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36'
        ]
        
        self.context = self.browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Create a new page
        self.page = self.context.new_page()
        
    def __del__(self):
        """Clean up resources."""
        try:
            if hasattr(self, 'page'):
                self.page.close()
            if hasattr(self, 'context'):
                self.context.close()
            if hasattr(self, 'browser'):
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()
        except:
            pass
            
    def _get_random_delay(self) -> float:
        """Get random delay between requests."""
        return random.uniform(2.0, 4.0)
    
    def _is_processed(self, url: str) -> bool:
        """Check if URL has been processed."""
        with self.url_lock:
            return url in self.processed_urls
            
    def _mark_processed(self, url: str):
        """Mark URL as processed."""
        with self.url_lock:
            self.processed_urls.add(url)
            
    def _extract_article_content(self, url: str) -> Optional[Dict]:
        """Extract content from an IAEA article."""
        try:
            if self._is_processed(url):
                return None
                
            # Skip non-article pages
            if any(x in url for x in ['/multimedia/', '/nuclear-explained/', '/press/contacts', '/statements', '/pressreleases']):
                return None
                
            # Navigate to the article
            self.page.goto(url, wait_until='networkidle')
            time.sleep(self._get_random_delay())  # Random delay
            
            # Scroll to trigger lazy loading
            self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1)
            self.page.evaluate('window.scrollTo(0, 0)')
            
            # Get title
            title = None
            title_elem = self.page.locator('h1').first
            if title_elem:
                title = title_elem.text_content().strip()
                
            if not title:
                logger.warning(f"No title found for article: {url}")
                return None
            
            # Get date
            date = None
            date_selectors = [
                'div.date-display-single',
                'time',
                'span.date',
                'div.submitted',
                'div.field--name-field-news-date'
            ]
            
            for selector in date_selectors:
                try:
                    date_elem = self.page.locator(selector).first
                    if date_elem:
                        date = date_elem.text_content().strip()
                        break
                except:
                    continue
            
            # Get content
            content = None
            content_parts = []
            
            # Try multiple content extraction methods
            content_selectors = [
                'div.field--name-body',
                'div.field--type-text-with-summary',
                'div.news-story-text',
                'div.node__content',
                'div.field--name-field-article-content',
                'div.field--name-field-press-release-content',
                'article',
                'main'
            ]
            
            for selector in content_selectors:
                if content:
                    break
                    
                try:
                    content_div = self.page.locator(selector).first
                    if content_div:
                        # Get all paragraphs and text elements
                        text_elements = content_div.locator('p, div, span, li').all()
                        
                        for elem in text_elements:
                            # Skip elements that are likely to be metadata
                            class_name = elem.get_attribute('class') or ''
                            if any(x in class_name for x in ['date', 'submitted', 'meta', 'social', 'share']):
                                continue
                                
                            text = elem.text_content().strip()
                            if text and len(text) > 20:  # Skip very short fragments
                                content_parts.append(text)
                        
                        if content_parts:
                            content = ' '.join(content_parts)
                            break
                except:
                    continue
            
            if not content or len(content.strip()) < 100:
                logger.warning(f"No substantial content found for article: {url}")
                return None
            
            # Clean up the content
            content = re.sub(r'\s+', ' ', content)
            content = content.replace('�', "'")
            
            # Get topics/tags
            topics = []
            topic_selectors = [
                'div.field--name-field-topics',
                'div.topics',
                'div.tags'
            ]
            
            for selector in topic_selectors:
                try:
                    topic_elements = self.page.locator(f"{selector} a, {selector} div, {selector} span").all()
                    topics.extend([elem.text_content().strip() for elem in topic_elements if elem.text_content().strip()])
                except:
                    continue
                    
            topics = list(set(topics))  # Remove duplicates
            
            return {
                'title': title,
                'content': content,
                'url': url,
                'date': date,
                'topics': topics,
                'source': 'IAEA'
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return None
            
    def _process_page(self, page: int) -> List[Dict]:
        """Process a single IAEA page.
        
        Args:
            page: Page number to process
            
        Returns:
            List[Dict]: List of articles from this page
        """
        articles = []
        page_url = f"{self.base_url}/news?topics=All&type=All&keywords=&page={page}"
        
        if self._is_processed(page_url):
            return articles
            
        logger.info(f"Processing IAEA page {page}")
        
        try:
            # Navigate to the page
            self.page.goto(page_url, wait_until='networkidle')
            time.sleep(self._get_random_delay())  # Random delay
            
            # Scroll to trigger lazy loading
            self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1)
            self.page.evaluate('window.scrollTo(0, 0)')
            
            # Get all article links
            article_links = []
            link_elements = self.page.locator('a').all()
            
            for link in link_elements:
                try:
                    href = link.get_attribute('href')
                    if href and ('/news/' in href or '/newscenter/' in href):
                        # Join base URL with relative path
                        if not href.startswith('http'):
                            href = f"{self.base_url}{href}"
                        article_links.append(href)
                except:
                    continue
            
            # Remove duplicates while preserving order
            article_links = list(dict.fromkeys(article_links))
            
            # Filter out non-article pages
            article_links = [
                link for link in article_links
                if not any(x in link for x in [
                    '/multimedia/',
                    '/nuclear-explained/',
                    '/press/contacts',
                    '/statements',
                    '/pressreleases'
                ])
            ]
            
            logger.info(f"Found {len(article_links)} potential articles on page {page}")
            
            # Process each article
            for href in article_links:
                if not self._is_processed(href):
                    article_data = self._extract_article_content(href)
                    if article_data:
                        articles.append(article_data)
                        self._mark_processed(href)
                        logger.info(f"Successfully processed article: {article_data['title']}")
                    
                    # Small delay between articles
                    time.sleep(self._get_random_delay())
            
        except Exception as e:
            logger.error(f"Error processing page {page}: {str(e)}")
        
        logger.info(f"Completed page {page}, found {len(articles)} articles")
        return articles
    
    def scrape_articles(self, start_page: int = 0, end_page: int = 691) -> List[Dict]:
        """Scrape IAEA articles from the specified page range."""
        all_articles = []
        
        try:
            # Calculate number of pages to process
            num_pages = end_page - start_page + 1
            
            # Process pages in chunks
            for chunk_start in range(start_page, end_page + 1, self.chunk_size):
                chunk_end = min(chunk_start + self.chunk_size, end_page + 1)
                logger.info(f"Processing pages {chunk_start} to {chunk_end-1}")
                
                # Process each page in the chunk
                for page in range(chunk_start, chunk_end):
                    articles = self._process_page(page)
                    all_articles.extend(articles)
                    logger.info(f"Found {len(articles)} articles on page {page}")
                
                logger.info(f"Chunk complete. Total articles so far: {len(all_articles)}")
                
                # Save progress after each chunk
                self._save_progress(all_articles)
                
                # Small delay between chunks to be nice to the server
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            # Save what we have so far
            self._save_progress(all_articles)
            
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
        """Save scraped articles to a JSON file."""
        if not articles:
            return
            
        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)
        
        # Create timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/iaea_articles_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            logger.info(f"Progress saved to: {filename}")
        except Exception as e:
            logger.error(f"Error saving progress: {str(e)}")
