"""News scraper for nuclear energy related articles."""
import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime
import time
from typing import List, Dict, Optional, Set
import logging
from urllib.parse import urljoin
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue
import math
import re
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NewsScraper:
    """Scraper for nuclear energy news articles."""
    
    def __init__(self, max_workers: int = 3, chunk_size: int = 2):
        """Initialize the scraper.
        
        Args:
            max_workers: Maximum number of parallel workers
            chunk_size: Number of pages to process in each chunk
        """
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.session = requests.Session()
        # Set up headers to simulate a browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
        self.iaea_base_url = "https://www.iaea.org"
        self.bloomberg_rss_urls = [
            "https://feeds.bloomberg.com/technology/rss",
            "https://feeds.bloomberg.com/energy/rss",
            "https://feeds.bloomberg.com/markets/rss"
        ]
        self.processed_urls = set()
        self.url_lock = threading.Lock()
        
    def _get_random_delay(self) -> float:
        """Get random delay between requests."""
        return random.uniform(0.5, 1.5)
    
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make HTTP request with error handling."""
        try:
            time.sleep(self._get_random_delay())  # Be nice to servers
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None
            
    def _is_processed(self, url: str) -> bool:
        """Check if URL has been processed."""
        with self.url_lock:
            return url in self.processed_urls
            
    def _mark_processed(self, url: str):
        """Mark URL as processed."""
        with self.url_lock:
            self.processed_urls.add(url)
    
    def _is_nuclear_related(self, title: str, content: str) -> bool:
        """Always return True - no filtering"""
        # Nuclear keywords for future filtering:
        # nuclear_keywords = {
        #     # Nuclear Power and Technology
        #     'nuclear', 'reactor', 'power plant', 'npp', 'smr', 'small modular reactor',
        #     'uranium', 'plutonium', 'thorium', 'fuel', 'enrichment', 'fusion', 'fission',
        #     
        #     # Nuclear Safety and Incidents
        #     'chernobyl', 'fukushima', 'three mile island', 'accident', 'incident', 'safety',
        #     'radiation', 'contamination', 'leak', 'meltdown', 'emergency', 'evacuation',
        #     
        #     # Nuclear Security and Safeguards
        #     'safeguards', 'non-proliferation', 'proliferation', 'security', 'verification',
        #     'inspection', 'monitoring', 'containment', 'surveillance',
        #     
        #     # Nuclear Applications
        #     'radiotherapy', 'isotope', 'radioisotope', 'medical', 'cancer', 'treatment',
        #     'imaging', 'diagnosis', 'agriculture', 'food', 'irradiation',
        #     
        #     # Nuclear Waste and Environment
        #     'waste', 'disposal', 'storage', 'repository', 'spent fuel', 'decommissioning',
        #     'environmental', 'contamination', 'cleanup', 'remediation',
        #     
        #     # Nuclear Organizations and Treaties
        #     'iaea', 'nrc', 'regulatory', 'treaty', 'convention', 'agreement', 'protocol',
        #     'declaration', 'cooperation', 'partnership'
        # }
        # 
        # # Convert text to lowercase for case-insensitive matching
        # text = (title + ' ' + content).lower()
        # 
        # # Check for keyword matches
        # return any(keyword in text for keyword in nuclear_keywords)
        
        return True
        
    def _get_iaea_page_articles(self, page_num: int) -> List[str]:
        """Get articles from a single IAEA news page."""
        try:
            # Construct page URL
            url = f"https://www.iaea.org/newscenter/news?page={page_num}"
            
            # Add headers to mimic browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Get the page
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all article links
            article_urls = []
            
            # Find all article containers
            articles = soup.find_all('div', class_='views-row')
            
            for article in articles:
                # Find link in article
                link = article.find('a')
                if link and link.get('href'):
                    href = link['href']
                    # Make sure it's an absolute URL
                    if href.startswith('/'):
                        href = f"https://www.iaea.org{href}"
                    article_urls.append(href)
            
            # Remove duplicates while preserving order
            article_urls = list(dict.fromkeys(article_urls))
            
            logger.info(f"Found {len(article_urls)} articles on page {page_num}")
            return article_urls
            
        except Exception as e:
            logger.error(f"Error getting articles from page {page_num}: {str(e)}")
            return []
            
    def _extract_iaea_content(self, url):
        """Extract content from an IAEA article."""
        try:
            if self._is_processed(url):
                return None
                
            # Add referer header for this specific request
            headers = self.session.headers.copy()
            headers['Referer'] = 'https://www.iaea.org/news'
            
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get title
            title = None
            title_selectors = [
                'h1.page-title',
                'h1.node-title',
                'h1.title',
                'h1'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
                    
            if not title:
                logger.warning(f"No title found for article: {url}")
                return None
            
            # Get content from article body
            content = None
            
            # First try to get content from field-name-body
            body = soup.find('div', class_='field-name-body')
            if body:
                paragraphs = body.find_all(['p', 'div'])
                content_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:  # Skip very short fragments
                        content_parts.append(text)
                if content_parts:
                    content = ' '.join(content_parts)
            
            if not content:
                # Try to get content from the news-story-text class
                news_story = soup.find('div', class_='news-story-text')
                if news_story:
                    paragraphs = news_story.find_all(['p', 'div'])
                    content_parts = []
                    for p in paragraphs:
                        if not any(x in p.get('class', []) for x in ['date', 'submitted', 'meta']):
                            text = p.get_text(strip=True)
                            if text and len(text) > 20:  # Skip very short fragments
                                content_parts.append(text)
                    if content_parts:
                        content = ' '.join(content_parts)
            
            if not content:
                # Try alternative content areas
                content_selectors = [
                    'div.node__content',
                    'div.field--type-text-with-summary',
                    'div.field--name-field-article-content',
                    'div.field--name-field-press-release-content',
                    'article',
                    'main'
                ]
                
                for selector in content_selectors:
                    content_div = soup.find('div', class_=selector.replace('div.', '')) if selector.startswith('div.') else soup.find(selector)
                    if content_div:
                        paragraphs = content_div.find_all(['p', 'div.field--item', 'div.field-item'])
                        content_parts = []
                        for p in paragraphs:
                            if not any(x in p.get('class', []) for x in ['date', 'submitted', 'meta']):
                                text = p.get_text(strip=True)
                                if text and len(text) > 20:  # Skip very short fragments
                                    content_parts.append(text)
                        if content_parts:
                            content = ' '.join(content_parts)
                            break
            
            if not content:
                # Try to find content in JavaScript data
                script_tags = soup.find_all('script', type='application/json')
                for script in script_tags:
                    try:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            # Look for content in common JSON structures
                            content_fields = ['body', 'content', 'text', 'article', 'description']
                            for field in content_fields:
                                if field in data:
                                    content = data[field]
                                    if isinstance(content, dict) and 'value' in content:
                                        content = content['value']
                                    if isinstance(content, str) and len(content.strip()) >= 100:
                                        # Clean HTML tags if present
                                        content = BeautifulSoup(content, 'html.parser').get_text(strip=True)
                                        break
                            if content:
                                break
                    except (json.JSONDecodeError, AttributeError):
                        continue
            
            if not content or len(content.strip()) < 100:
                logger.warning(f"No substantial content found for article: {url}")
                return None
            
            # Clean up the content
            content = re.sub(r'\s+', ' ', content)
            content = content.replace('�', "'")
            content = BeautifulSoup(content, 'html.parser').get_text(strip=True)  # Final HTML cleanup
            
            return {
                'title': title,
                'content': content,
                'url': url,
                'source': 'IAEA'
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return None

    def _process_iaea_page(self, page: int) -> List[Dict]:
        """Process a single IAEA page.
        
        Args:
            page: Page number to process
            
        Returns:
            List[Dict]: List of articles from this page
        """
        articles = []
        page_url = f"{self.iaea_base_url}/newscenter/news?page={page}"
        
        if self._is_processed(page_url):
            return articles
            
        logger.info(f"Processing IAEA page {page}")
        
        response = self._make_request(page_url)
        if not response:
            return articles
            
        self._mark_processed(page_url)
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all article links in the main content area
        # Look for articles in the news listing page
        article_containers = (
            soup.find_all('div', class_='news-item') or 
            soup.find_all('div', class_='views-row') or
            soup.find_all('article') or
            soup.find_all('div', class_='node--type-news')
        )
        
        if not article_containers:
            # Try finding links directly if no containers found
            main_content = (
                soup.find('main', id='main-content') or
                soup.find('div', class_='main-content') or
                soup.find('div', class_='content') or
                soup
            )
            article_links = main_content.find_all('a', href=lambda x: x and ('/news/' in x or '/newscenter/' in x))
            
            # Create artificial containers for processing
            article_containers = [{'link': link} for link in article_links]
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {}
            
            for container in article_containers:
                # Handle both actual containers and our artificial ones
                if isinstance(container, dict):
                    link = container['link']
                else:
                    link = container.find('a', href=True)
                
                if not link or not link.get('href'):
                    continue
                    
                article_url = urljoin(self.iaea_base_url, link['href'])
                if not self._is_processed(article_url):
                    future_to_url[executor.submit(self._extract_iaea_content, article_url)] = article_url
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    article_data = future.result()
                    if article_data:
                        articles.append(article_data)
                        self._mark_processed(url)
                        logger.info(f"Successfully processed article: {article_data['title']}")
                except Exception as e:
                    logger.error(f"Error processing article {url}: {str(e)}")
        
        logger.info(f"Completed page {page}, found {len(articles)} articles")
        return articles
    
    def scrape_iaea_articles(self, start_page: int = 0, end_page: int = 5) -> List[Dict]:
        """Scrape IAEA articles from the specified page range."""
        articles = []
        
        try:
            # Calculate number of pages to process
            num_pages = end_page - start_page
            chunk_size = 2  # Process 2 pages at a time
            num_chunks = math.ceil(num_pages / chunk_size)
            
            logger.info(f"Starting IAEA scraping from page {start_page} to {end_page}")
            logger.info(f"Processing in {num_chunks} chunks of {chunk_size} pages each")
            
            for chunk in range(num_chunks):
                chunk_start = start_page + (chunk * chunk_size)
                chunk_end = min(chunk_start + chunk_size, end_page)
                
                logger.info(f"Processing chunk {chunk + 1}/{num_chunks} (pages {chunk_start}-{chunk_end - 1})")
                
                # Process pages in this chunk
                chunk_articles = []
                for page in range(chunk_start, chunk_end):
                    # Get article URLs from this page
                    page_articles = self._get_iaea_page_articles(page)
                    
                    if page_articles:
                        # Process each article URL
                        for article_url in page_articles:
                            article_data = self._extract_iaea_content(article_url)
                            if article_data:
                                chunk_articles.append(article_data)
                                
                    logger.info(f"Found {len(chunk_articles)} articles on page {page}")
                    logger.info(f"Completed page {page}, found {len(chunk_articles)} articles")
                
                # Add chunk articles to main list
                articles.extend(chunk_articles)
                logger.info(f"Chunk {chunk + 1} complete. Total articles so far: {len(articles)}")
                
                # Sleep between chunks to avoid overwhelming the server
                if chunk < num_chunks - 1:
                    time.sleep(1)
            
            logger.info(f"Found {len(articles)} relevant IAEA articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping IAEA articles: {str(e)}")
            return articles
    
    def scrape_bloomberg_rss(self) -> List[Dict]:
        """Scrape nuclear-related articles from Bloomberg RSS feeds."""
        articles = []
        
        with ThreadPoolExecutor(max_workers=len(self.bloomberg_rss_urls)) as executor:
            future_to_url = {
                executor.submit(self._process_bloomberg_feed, url): url 
                for url in self.bloomberg_rss_urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    feed_articles = future.result()
                    articles.extend(feed_articles)
                except Exception as e:
                    logger.error(f"Error processing Bloomberg feed {url}: {str(e)}")
        
        return articles
    
    def _process_bloomberg_feed(self, rss_url: str) -> List[Dict]:
        """Process a single Bloomberg RSS feed."""
        articles = []
        
        try:
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries:
                # Check if article is related to nuclear
                keywords = ['nuclear', 'reactor', 'radiation', 'isotope', 'uranium', 
                          'safety', 'energy', 'power plant', 'radioactive', 'atomic',
                          'regulatory', 'safeguards']
                          
                if any(keyword in entry.title.lower() or 
                       keyword in entry.description.lower() 
                       for keyword in keywords):
                    
                    article = {
                        'title': entry.title,
                        'date': datetime.fromtimestamp(time.mktime(entry.published_parsed)).isoformat(),
                        'content': entry.description,
                        'url': entry.link,
                        'source': 'Bloomberg'
                    }
                    
                    articles.append(article)
                    logger.info(f"Found relevant Bloomberg article: {article['title']}")
        
        except Exception as e:
            logger.error(f"Error parsing Bloomberg RSS feed {rss_url}: {str(e)}")
        
        return articles
    
    def scrape_all_sources(self, start_page: int = 0, end_page: int = 5) -> List[Dict]:
        """Scrape articles from all sources.
        
        Args:
            start_page: First IAEA page to scrape
            end_page: Last IAEA page to scrape
            
        Returns:
            List[Dict]: Combined list of articles from all sources
        """
        all_articles = []
        
        # Scrape IAEA
        iaea_articles = self.scrape_iaea_articles(start_page=start_page, end_page=end_page)
        all_articles.extend(iaea_articles)
        logger.info(f"Found {len(iaea_articles)} relevant IAEA articles")
        
        # Scrape Bloomberg
        bloomberg_articles = self.scrape_bloomberg_rss()
        all_articles.extend(bloomberg_articles)
        logger.info(f"Found {len(bloomberg_articles)} relevant Bloomberg articles")
        
        return all_articles
