"""Google News scraper with advanced features.

This module provides a specialized scraper for Google News that:
1. Uses weekly date ranges to ensure comprehensive coverage
2. Implements advanced anti-detection techniques
3. Targets specific news sources (Bloomberg, Reuters, FT)
4. Handles pagination and dynamic loading
"""
import os
import time
import random
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, quote_plus
import concurrent.futures

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('google_news_scraping.log')
    ]
)
logger = logging.getLogger(__name__)

class GoogleNewsScraper:
    """Advanced Google News scraper with anti-detection and comprehensive coverage."""
    
    def __init__(self, 
                 headless: bool = True,
                 use_proxy: bool = False,
                 max_workers: int = 3,
                 data_dir: str = 'data/google_news',
                 delay_range: Tuple[float, float] = (2.0, 5.0)):
        """Initialize the Google News scraper.
        
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
        
        # Target sources
        self.target_sources = {
            'bloomberg.com': 'Bloomberg',
            'reuters.com': 'Reuters',
            'ft.com': 'Financial Times'
        }
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Set of processed URLs to avoid duplicates
        self.processed_urls = set()
        
    def _get_random_delay(self) -> float:
        """Get random delay between requests."""
        return random.uniform(self.delay_range[0], self.delay_range[1])
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Set up and return an undetectable Chrome WebDriver."""
        try:
            # Initialize options with undetected_chromedriver
            options = uc.ChromeOptions()
            
            # Add anti-detection measures
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-browser-side-navigation')
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_argument('--start-maximized')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'--user-agent={self.user_agent.random}')
            
            # Set page load strategy to eager to avoid waiting for all resources
            options.page_load_strategy = 'eager'
            
            if self.headless:
                options.add_argument('--headless=new')  # Use new headless mode
            
            # Create undetectable Chrome driver with a longer timeout
            driver = uc.Chrome(
                options=options,
                driver_executable_path=None,  # Let it auto-download
                browser_executable_path=None,  # Use default Chrome
                suppress_welcome=True,
                use_subprocess=True,
            )
            
            # Set window size explicitly after creation
            driver.set_window_size(1920, 1080)
            
            # Add additional JavaScript to make detection harder
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    window.chrome = {
                        runtime: {}
                    };
                """
            })
            
            return driver
            
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {str(e)}")
            raise
    
    def _format_google_date(self, date_str: str) -> str:
        """Format date for Google News URL."""
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%m/%d/%Y')
    
    def _generate_weekly_ranges(self, start_date: str, end_date: str) -> List[Tuple[str, str]]:
        """Generate weekly date ranges between start and end dates."""
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        date_ranges = []
        current = start
        
        while current < end:
            week_end = min(current + timedelta(days=6), end)
            date_ranges.append((
                current.strftime('%Y-%m-%d'),
                week_end.strftime('%Y-%m-%d')
            ))
            current = week_end + timedelta(days=1)
        
        return date_ranges
    
    def _build_search_url(self, query: str, start_date: str, end_date: str, source: str = None) -> str:
        """Build Google News search URL with date range and optional source filter."""
        base_url = "https://www.google.com/search"
        
        # Format dates for Google
        after = self._format_google_date(start_date)
        before = self._format_google_date(end_date)
        
        # Build search query
        search_query = quote_plus(query)
        if source:
            search_query = f"{search_query} site:{source}"
        
        # Construct URL with parameters
        params = [
            ("q", search_query),
            ("tbm", "nws"),  # News search
            ("tbs", f"cdr:1,cd_min:{after},cd_max:{before}"),  # Date range
            ("hl", "en"),  # English language
            ("gl", "en"),  # Global search
            ("num", "100")  # Maximum results per page
        ]
        
        url = f"{base_url}?" + "&".join(f"{k}={v}" for k, v in params)
        return url
    
    def _extract_article_info(self, element: BeautifulSoup) -> Optional[Dict]:
        """Extract article information from a Google News result element."""
        try:
            # Find the main link
            link = element.find('a')
            if not link:
                return None
                
            url = link.get('href', '')
            
            # Check if URL is from target sources
            domain = urlparse(url).netloc.replace('www.', '')
            source = next((name for site, name in self.target_sources.items() 
                         if site in domain), None)
            if not source:
                return None
            
            # Extract title
            title = link.get_text(strip=True)
            if not title:
                return None
            
            # Extract date
            date_element = element.find('time')
            if date_element:
                date = date_element.get_text(strip=True)
            else:
                # Try alternative date formats
                date_text = element.find(class_=['date', 'time', 'datetime'])
                date = date_text.get_text(strip=True) if date_text else None
            
            # Extract snippet
            snippet = element.find(class_=['snippet', 'description'])
            snippet_text = snippet.get_text(strip=True) if snippet else None
            
            return {
                'title': title,
                'url': url,
                'date': date,
                'source': source,
                'snippet': snippet_text
            }
            
        except Exception as e:
            logger.error(f"Error extracting article info: {str(e)}")
            return None
    
    def _scroll_to_bottom(self, driver: webdriver.Chrome):
        """Scroll to bottom of page and wait for new content to load."""
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Scroll down
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Calculate new scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            # Break if no more content loaded
            if new_height == last_height:
                break
                
            last_height = new_height
            
            # Add random delay to avoid detection
            time.sleep(self._get_random_delay())
    
    def _handle_captcha(self, driver: webdriver.Chrome) -> bool:
        """Handle Google captcha if present."""
        try:
            # Check for common captcha indicators
            captcha_selectors = [
                "//iframe[contains(@src, 'recaptcha')]",
                "//div[contains(@class, 'g-recaptcha')]",
                "//form[@action='/sorry']"
            ]
            
            for selector in captcha_selectors:
                if driver.find_elements(By.XPATH, selector):
                    logger.warning("Captcha detected! Implementing bypass strategy...")
                    
                    # Wait for a longer period
                    time.sleep(10 + self._get_random_delay())
                    
                    # Simulate human-like behavior
                    actions = ActionChains(driver)
                    actions.move_by_offset(random.randint(0, 100), random.randint(0, 100))
                    actions.move_by_offset(0, 0)
                    actions.perform()
                    
                    # Try to switch to recaptcha frame
                    frames = driver.find_elements(By.TAG_NAME, "iframe")
                    for frame in frames:
                        if "recaptcha" in frame.get_attribute("src").lower():
                            driver.switch_to.frame(frame)
                            checkbox = WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.ID, "recaptcha-anchor"))
                            )
                            checkbox.click()
                            time.sleep(2)
                            driver.switch_to.default_content()
                            return True
                    
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling captcha: {str(e)}")
            return False
    
    def _search_articles(self, query: str, start_date: str, end_date: str, source: str) -> List[Dict]:
        """Search Google News for articles from a specific source within date range."""
        logger.info(f"Searching {source} articles for '{query}' from {start_date} to {end_date}")
        
        articles = []
        driver = self._setup_driver()
        
        try:
            # Build search URL
            url = self._build_search_url(query, start_date, end_date, source)
            driver.get(url)
            time.sleep(self._get_random_delay())
            
            # Handle captcha if present
            if not self._handle_captcha(driver):
                logger.error("Failed to handle captcha")
                return articles
            
            # Wait for search results
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "g"))
            )
            
            # Scroll to load all results
            self._scroll_to_bottom(driver)
            
            # Parse results
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            results = soup.find_all(class_="g")
            
            for result in results:
                article = self._extract_article_info(result)
                if article and article['url'] not in self.processed_urls:
                    articles.append(article)
                    self.processed_urls.add(article['url'])
            
            logger.info(f"Found {len(articles)} articles from {source}")
            return articles
            
        except Exception as e:
            logger.error(f"Error searching {source}: {str(e)}")
            return articles
            
        finally:
            driver.quit()
    
    def search_all_sources(self, query: str, start_date: str, end_date: str) -> List[Dict]:
        """Search all target sources for articles within the date range."""
        all_articles = []
        
        # Generate weekly date ranges
        date_ranges = self._generate_weekly_ranges(start_date, end_date)
        logger.info(f"Generated {len(date_ranges)} weekly ranges")
        
        # Search each source for each week
        for source_domain, source_name in self.target_sources.items():
            for week_start, week_end in date_ranges:
                try:
                    # Add random delay between weeks
                    time.sleep(self._get_random_delay())
                    
                    articles = self._search_articles(query, week_start, week_end, source_domain)
                    all_articles.extend(articles)
                    
                    logger.info(
                        f"Completed {source_name} search for week {week_start} to {week_end}: "
                        f"{len(articles)} articles found"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Error searching {source_name} for week {week_start} to {week_end}: "
                        f"{str(e)}"
                    )
        
        logger.info(f"Total articles found across all sources: {len(all_articles)}")
        return all_articles
    
    def save_articles(self, articles: List[Dict], filename: str = None) -> str:
        """Save articles to a JSON file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"google_news_articles_{timestamp}.json"
        
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(articles)} articles to {filepath}")
        return filepath
    
    def save_to_csv(self, articles: List[Dict], filename: str = None) -> str:
        """Save articles to a CSV file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"google_news_articles_{timestamp}.csv"
        
        filepath = os.path.join(self.data_dir, filename)
        
        # Convert to DataFrame and save
        df = pd.DataFrame(articles)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        logger.info(f"Saved {len(articles)} articles to {filepath}")
        return filepath
    
    def run(self, query: str, start_date: str, end_date: str) -> List[Dict]:
        """Run the Google News scraper for the given query and date range."""
        logger.info(
            f"Starting Google News scraper for query '{query}' "
            f"from {start_date} to {end_date}"
        )
        
        # Search all sources with weekly ranges
        articles = self.search_all_sources(query, start_date, end_date)
        
        # Save results
        if articles:
            self.save_articles(articles)
            self.save_to_csv(articles)
        
        return articles
