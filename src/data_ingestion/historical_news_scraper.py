"""Historical news scraper for financial news sources.

This module provides a scraper for historical news articles from various financial
news sources including Bloomberg, Reuters, and Financial Times without using their
official APIs. It uses Selenium for browser automation to handle JavaScript-heavy
sites and implements techniques to avoid detection.
"""
import os
import time
import random
import json
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import concurrent.futures
import hashlib

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import pandas as pd
from newspaper import Article
from newspaper.article import ArticleException
import trafilatura
from readability import Document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('historical_scraping.log')
    ]
)
logger = logging.getLogger(__name__)

class HistoricalNewsScraper:
    """Scraper for historical financial news articles."""
    
    def __init__(self, 
                 headless: bool = True, 
                 use_proxy: bool = False,
                 max_workers: int = 3,
                 data_dir: str = 'data/historical_news',
                 delay_range: Tuple[float, float] = (1.0, 3.0)):
        """Initialize the historical news scraper.
        
        Args:
            headless: Whether to run the browser in headless mode
            use_proxy: Whether to use proxy rotation
            max_workers: Maximum number of parallel workers
            data_dir: Directory to store scraped data
            delay_range: Range for random delay between requests (min, max)
        """
        self.headless = headless
        self.use_proxy = use_proxy
        self.max_workers = max_workers
        self.data_dir = data_dir
        self.delay_range = delay_range
        self.user_agent = UserAgent()
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
        
        # Set of processed URLs to avoid duplicates
        self.processed_urls = set()
        
        # Source-specific configurations
        self.sources = {
            'bloomberg': {
                'search_url': 'https://www.bloomberg.com/search?query={query}&time={time_range}',
                'article_selector': '.search-result-story__headline',
                'date_selector': '.search-result-story__metadata'
            },
            'reuters': {
                'search_url': 'https://www.reuters.com/site-search/?query={query}&offset=0&date={date_range}',
                'article_selector': '.search-result__title',
                'date_selector': '.search-result__timestamp'
            },
            'ft': {
                'search_url': 'https://www.ft.com/search?q={query}&dateTo={date_to}&dateFrom={date_from}',
                'article_selector': '.o-teaser__heading',
                'date_selector': '.o-date'
            }
        }
    
    def _get_random_delay(self) -> float:
        """Get random delay between requests."""
        return random.uniform(self.delay_range[0], self.delay_range[1])
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Set up and return a Selenium WebDriver."""
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        
        # Add common options to avoid detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument(f"user-agent={self.user_agent.random}")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Create and return the driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Set window size to a common resolution
        driver.set_window_size(1920, 1080)
        
        # Execute CDP commands to prevent detection
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        return driver
    
    def _extract_article_content(self, url: str) -> Dict:
        """Extract article content using multiple methods for robustness."""
        try:
            # First try with newspaper3k
            article = Article(url)
            article.download()
            article.parse()
            
            # If content is too short, try with trafilatura
            if len(article.text) < 200:
                response = self.session.get(url, timeout=10)
                downloaded = trafilatura.fetch_url(url)
                if downloaded:
                    content = trafilatura.extract(downloaded)
                    if content and len(content) > len(article.text):
                        article.text = content
            
            # If still too short, try with readability
            if len(article.text) < 200:
                response = self.session.get(url, timeout=10)
                doc = Document(response.text)
                readable_content = doc.summary()
                soup = BeautifulSoup(readable_content, 'html.parser')
                readable_text = soup.get_text(separator='\n', strip=True)
                if len(readable_text) > len(article.text):
                    article.text = readable_text
            
            # Create article data dictionary
            article_data = {
                'title': article.title,
                'url': url,
                'text': article.text,
                'authors': article.authors,
                'publish_date': article.publish_date.isoformat() if article.publish_date else None,
                'top_image': article.top_image,
                'keywords': article.keywords,
                'summary': article.summary,
                'scraped_at': datetime.now().isoformat()
            }
            
            return article_data
            
        except (ArticleException, requests.RequestException) as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return {
                'url': url,
                'error': str(e),
                'scraped_at': datetime.now().isoformat()
            }
    
    def _search_bloomberg(self, query: str, start_date: str, end_date: str) -> List[Dict]:
        """Search Bloomberg for articles matching the query within the date range."""
        logger.info(f"Searching Bloomberg for '{query}' from {start_date} to {end_date}")
        
        # Format the time range for Bloomberg
        time_range = f"range[start]={start_date}&range[end]={end_date}"
        search_url = self.sources['bloomberg']['search_url'].format(
            query=query.replace(' ', '+'),
            time_range=time_range
        )
        
        driver = self._setup_driver()
        articles = []
        
        try:
            driver.get(search_url)
            time.sleep(self._get_random_delay())
            
            # Wait for search results to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.sources['bloomberg']['article_selector']))
            )
            
            # Scroll down to load more results (Bloomberg uses lazy loading)
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Parse the search results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            article_elements = soup.select(self.sources['bloomberg']['article_selector'])
            
            for element in article_elements:
                try:
                    # Extract article URL
                    link_element = element.find('a')
                    if not link_element:
                        continue
                    
                    article_url = link_element.get('href')
                    if not article_url.startswith('http'):
                        article_url = urljoin('https://www.bloomberg.com', article_url)
                    
                    # Skip if already processed
                    if article_url in self.processed_urls:
                        continue
                    
                    # Extract article title
                    title = link_element.get_text(strip=True)
                    
                    # Extract date if available
                    date_element = element.find_parent().select_one(self.sources['bloomberg']['date_selector'])
                    date = date_element.get_text(strip=True) if date_element else None
                    
                    # Add to articles list
                    articles.append({
                        'title': title,
                        'url': article_url,
                        'date': date,
                        'source': 'bloomberg'
                    })
                    
                    # Mark as processed
                    self.processed_urls.add(article_url)
                    
                except Exception as e:
                    logger.error(f"Error processing Bloomberg article: {str(e)}")
                    continue
            
            logger.info(f"Found {len(articles)} Bloomberg articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error searching Bloomberg: {str(e)}")
            return []
            
        finally:
            driver.quit()
    
    def _search_reuters(self, query: str, start_date: str, end_date: str) -> List[Dict]:
        """Search Reuters for articles matching the query within the date range."""
        logger.info(f"Searching Reuters for '{query}' from {start_date} to {end_date}")
        
        # Format the date range for Reuters
        date_range = f"from={start_date}&to={end_date}"
        search_url = self.sources['reuters']['search_url'].format(
            query=query.replace(' ', '+'),
            date_range=date_range
        )
        
        driver = self._setup_driver()
        articles = []
        
        try:
            driver.get(search_url)
            time.sleep(self._get_random_delay())
            
            # Wait for search results to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.sources['reuters']['article_selector']))
            )
            
            # Scroll down to load more results
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Parse the search results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            article_elements = soup.select(self.sources['reuters']['article_selector'])
            
            for element in article_elements:
                try:
                    # Extract article URL
                    link_element = element.find('a')
                    if not link_element:
                        continue
                    
                    article_url = link_element.get('href')
                    if not article_url.startswith('http'):
                        article_url = urljoin('https://www.reuters.com', article_url)
                    
                    # Skip if already processed
                    if article_url in self.processed_urls:
                        continue
                    
                    # Extract article title
                    title = link_element.get_text(strip=True)
                    
                    # Extract date if available
                    date_element = element.find_parent().select_one(self.sources['reuters']['date_selector'])
                    date = date_element.get_text(strip=True) if date_element else None
                    
                    # Add to articles list
                    articles.append({
                        'title': title,
                        'url': article_url,
                        'date': date,
                        'source': 'reuters'
                    })
                    
                    # Mark as processed
                    self.processed_urls.add(article_url)
                    
                except Exception as e:
                    logger.error(f"Error processing Reuters article: {str(e)}")
                    continue
            
            logger.info(f"Found {len(articles)} Reuters articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error searching Reuters: {str(e)}")
            return []
            
        finally:
            driver.quit()
    
    def _search_financial_times(self, query: str, start_date: str, end_date: str) -> List[Dict]:
        """Search Financial Times for articles matching the query within the date range."""
        logger.info(f"Searching Financial Times for '{query}' from {start_date} to {end_date}")
        
        # Format the date range for FT
        search_url = self.sources['ft']['search_url'].format(
            query=query.replace(' ', '+'),
            date_from=start_date,
            date_to=end_date
        )
        
        driver = self._setup_driver()
        articles = []
        
        try:
            driver.get(search_url)
            time.sleep(self._get_random_delay())
            
            # Wait for search results to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.sources['ft']['article_selector']))
            )
            
            # Scroll down to load more results
            last_height = driver.execute_script("return document.body.scrollHeight")
            while True:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Parse the search results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            article_elements = soup.select(self.sources['ft']['article_selector'])
            
            for element in article_elements:
                try:
                    # Extract article URL
                    link_element = element.find('a')
                    if not link_element:
                        continue
                    
                    article_url = link_element.get('href')
                    if not article_url.startswith('http'):
                        article_url = urljoin('https://www.ft.com', article_url)
                    
                    # Skip if already processed
                    if article_url in self.processed_urls:
                        continue
                    
                    # Extract article title
                    title = link_element.get_text(strip=True)
                    
                    # Extract date if available
                    date_element = element.find_parent().select_one(self.sources['ft']['date_selector'])
                    date = date_element.get_text(strip=True) if date_element else None
                    
                    # Add to articles list
                    articles.append({
                        'title': title,
                        'url': article_url,
                        'date': date,
                        'source': 'ft'
                    })
                    
                    # Mark as processed
                    self.processed_urls.add(article_url)
                    
                except Exception as e:
                    logger.error(f"Error processing Financial Times article: {str(e)}")
                    continue
            
            logger.info(f"Found {len(articles)} Financial Times articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error searching Financial Times: {str(e)}")
            return []
            
        finally:
            driver.quit()
    
    def search_all_sources(self, query: str, start_date: str, end_date: str) -> List[Dict]:
        """Search all sources for articles matching the query within the date range."""
        all_articles = []
        
        # Use ThreadPoolExecutor to search sources in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit search tasks
            future_to_source = {
                executor.submit(self._search_bloomberg, query, start_date, end_date): 'bloomberg',
                executor.submit(self._search_reuters, query, start_date, end_date): 'reuters',
                executor.submit(self._search_financial_times, query, start_date, end_date): 'ft'
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                    logger.info(f"Completed search for {source}: {len(articles)} articles found")
                except Exception as e:
                    logger.error(f"Error searching {source}: {str(e)}")
        
        logger.info(f"Total articles found across all sources: {len(all_articles)}")
        return all_articles
    
    def fetch_article_content(self, articles: List[Dict]) -> List[Dict]:
        """Fetch full content for a list of articles."""
        articles_with_content = []
        
        # Use ThreadPoolExecutor to fetch content in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit content extraction tasks
            future_to_article = {
                executor.submit(self._extract_article_content, article['url']): article
                for article in articles
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_article):
                article = future_to_article[future]
                try:
                    content = future.result()
                    # Merge the original article data with the content
                    full_article = {**article, **content}
                    articles_with_content.append(full_article)
                    logger.info(f"Fetched content for: {article['title'][:50]}...")
                except Exception as e:
                    logger.error(f"Error fetching content for {article['url']}: {str(e)}")
                    # Add the article with an error flag
                    article['error'] = str(e)
                    articles_with_content.append(article)
        
        return articles_with_content
    
    def save_articles(self, articles: List[Dict], filename: str = None) -> str:
        """Save articles to a JSON file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"articles_{timestamp}.json"
        
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(articles)} articles to {filepath}")
        return filepath
    
    def save_to_csv(self, articles: List[Dict], filename: str = None) -> str:
        """Save articles to a CSV file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"articles_{timestamp}.csv"
        
        filepath = os.path.join(self.data_dir, filename)
        
        # Convert to DataFrame and save
        df = pd.DataFrame(articles)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        logger.info(f"Saved {len(articles)} articles to {filepath}")
        return filepath
    
    def run(self, query: str, start_date: str, end_date: str, fetch_content: bool = True) -> List[Dict]:
        """Run the scraper for the given query and date range."""
        logger.info(f"Starting historical news scraper for query '{query}' from {start_date} to {end_date}")
        
        # Search all sources
        articles = self.search_all_sources(query, start_date, end_date)
        
        # Fetch content if requested
        if fetch_content and articles:
            articles = self.fetch_article_content(articles)
        
        # Save results
        if articles:
            self.save_articles(articles)
            self.save_to_csv(articles)
        
        return articles 