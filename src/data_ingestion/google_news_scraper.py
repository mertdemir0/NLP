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
        self.logger = logging.getLogger(__name__)
        self.headless = headless
        self.use_proxy = use_proxy
        self.max_workers = max_workers
        self.data_dir = data_dir
        self.delay_range = delay_range
        self.driver = None
        
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
        
        # Initialize the driver
        self._setup_driver()

    def __del__(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def _setup_driver(self):
        """Set up the undetected Chrome driver with optimal settings."""
        try:
            options = uc.ChromeOptions()
            
            if self.headless:
                options.add_argument('--headless')
            
            # Essential settings for undetectability
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-gpu')
            
            # Random window size for added variation
            width = random.randint(1200, 1600)
            height = random.randint(800, 1000)
            options.add_argument(f'--window-size={width},{height}')
            
            # Set random user agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
            ]
            options.add_argument(f'user-agent={random.choice(user_agents)}')
            
            # Initialize driver with retry mechanism
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.driver = uc.Chrome(options=options)
                    self.driver.set_page_load_timeout(30)
                    
                    # Set random geolocation
                    self.driver.execute_cdp_cmd('Emulation.setGeolocationOverride', {
                        'latitude': random.uniform(30, 50),
                        'longitude': random.uniform(-120, -70),
                        'accuracy': 100
                    })
                    
                    # Clear cookies and cache
                    self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
                    self.driver.execute_cdp_cmd('Network.clearBrowserCookies', {})
                    
                    break
                except Exception as e:
                    self.logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep((attempt + 1) * 2)

        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {str(e)}")
            raise

    def _get_random_delay(self) -> float:
        """Get random delay between requests."""
        return random.uniform(self.delay_range[0], self.delay_range[1])
    
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
            self.logger.error(f"Error extracting article info: {str(e)}")
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
                "//form[@action='/sorry']",
                "//div[contains(text(), 'unusual traffic')]",
                "//div[contains(text(), 'verify you are human')]"
            ]
            
            for selector in captcha_selectors:
                if driver.find_elements(By.XPATH, selector):
                    self.logger.warning("Captcha detected! Implementing bypass strategy...")
                    
                    # Save cookies before handling captcha
                    cookies = driver.get_cookies()
                    
                    # Clear cookies and cache
                    driver.delete_all_cookies()
                    driver.execute_script("window.localStorage.clear();")
                    driver.execute_script("window.sessionStorage.clear();")
                    
                    # Wait for a longer period with random delay
                    time.sleep(random.uniform(15, 30))
                    
                    # Restore original cookies
                    for cookie in cookies:
                        try:
                            driver.add_cookie(cookie)
                        except:
                            pass
                    
                    # Simulate human-like behavior
                    actions = ActionChains(driver)
                    
                    # Random mouse movements
                    for _ in range(5):
                        x_offset = random.randint(-100, 100)
                        y_offset = random.randint(-100, 100)
                        actions.move_by_offset(x_offset, y_offset)
                        actions.pause(random.uniform(0.1, 0.3))
                    
                    # Move to center
                    actions.move_to_element(driver.find_element(By.TAG_NAME, "body"))
                    actions.pause(random.uniform(0.5, 1.0))
                    
                    # Perform actions
                    actions.perform()
                    
                    # Try to switch to recaptcha frame
                    frames = driver.find_elements(By.TAG_NAME, "iframe")
                    for frame in frames:
                        try:
                            if "recaptcha" in frame.get_attribute("src").lower():
                                driver.switch_to.frame(frame)
                                
                                # Wait for checkbox
                                checkbox = WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.ID, "recaptcha-anchor"))
                                )
                                
                                # Move to checkbox with random approach
                                actions = ActionChains(driver)
                                actions.move_by_offset(random.randint(-50, 50), random.randint(-50, 50))
                                actions.pause(random.uniform(0.1, 0.3))
                                actions.move_to_element(checkbox)
                                actions.pause(random.uniform(0.2, 0.5))
                                actions.click()
                                actions.perform()
                                
                                time.sleep(random.uniform(2, 4))
                                driver.switch_to.default_content()
                                
                                # Check if captcha was solved
                                time.sleep(5)
                                if not any(driver.find_elements(By.XPATH, sel) for sel in captcha_selectors):
                                    return True
                        except:
                            continue
                    
                    # If we get here, we couldn't solve the captcha
                    self.logger.warning("Failed to solve captcha automatically")
                    return False
            
            # No captcha detected
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling captcha: {str(e)}")
            return False

    def _wait_and_find_element(self, by, value, timeout=20, retries=3):
        """Wait for and find an element with retries and dynamic waits."""
        for attempt in range(retries):
            try:
                wait = WebDriverWait(self.driver, timeout, poll_frequency=1)
                element = wait.until(EC.presence_of_element_located((by, value)))
                # Additional wait for interactability
                wait.until(EC.element_to_be_clickable((by, value)))
                return element
            except Exception as e:
                if attempt < retries - 1:
                    self.logger.info(f"Retry {attempt + 1}: Element {value} not ready, waiting...")
                    # Exponential backoff
                    time.sleep((attempt + 1) * random.uniform(2, 4))
                    # Refresh page on last retry
                    if attempt == retries - 2:
                        self.driver.refresh()
                else:
                    raise

    def _safe_get(self, url, max_retries=3):
        """Safely navigate to a URL with retries."""
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                # Wait for page load
                WebDriverWait(self.driver, 20).until(
                    lambda driver: driver.execute_script('return document.readyState') == 'complete'
                )
                return True
            except Exception as e:
                self.logger.error(f"Error navigating to {url}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep((attempt + 1) * random.uniform(2, 4))
                else:
                    raise

    def _human_click(self, element):
        """Simulate human-like clicking behavior."""
        try:
            # Move to element with random offset
            action = ActionChains(self.driver)
            action.move_to_element_with_offset(
                element,
                random.randint(-3, 3),
                random.randint(-3, 3)
            )
            action.pause(random.uniform(0.1, 0.3))
            action.click()
            action.perform()
            return True
        except Exception as e:
            self.logger.error(f"Error clicking element: {str(e)}")
            # Fallback to regular click
            element.click()

    def _human_type(self, element, text):
        """Simulate human-like typing behavior."""
        try:
            element.click()
            for char in text:
                element.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            return True
        except Exception as e:
            self.logger.error(f"Error typing text: {str(e)}")
            # Fallback to regular send_keys
            element.send_keys(text)

    def _get_random_delay(self):
        """Get a random delay between actions."""
        # 70% chance of short delay, 30% chance of longer delay
        if random.random() < 0.7:
            return random.uniform(2, 5)
        return random.uniform(5, 8)

    def _search_source(self, source: str, query: str, start_date: str, end_date: str):
        """Search for articles from a specific source within date range."""
        try:
            self.logger.info(f"Searching {source} articles for '{query}' from {start_date} to {end_date}")
            
            # Navigate directly to Google News search
            search_url = f"https://news.google.com/search?q=site:{source}%20{quote(query)}"
            self._safe_get(search_url)
            time.sleep(random.uniform(3, 5))
            
            # Wait for search box to be present
            search_box = self._wait_and_find_element(
                By.CSS_SELECTOR, 
                "input[type='text'], input[name='q'], input[aria-label*='Search']"
            )
            
            # Clear and type the query with date filter
            search_box.clear()
            time.sleep(random.uniform(1, 2))
            self._human_type(search_box, f"site:{source} {query} when:{start_date}-{end_date}")
            search_box.send_keys(Keys.RETURN)
            time.sleep(random.uniform(2, 4))
            
            # Scroll to load more results
            self._scroll_page()
            
            # Extract articles
            return self._extract_articles()
            
        except Exception as e:
            self.logger.error(f"Error searching {source}: {str(e)}")
            if "element not interactable" in str(e):
                self.logger.info("Page elements not ready, increasing wait time")
                time.sleep(random.uniform(5, 8))
            raise

    def _scroll_page(self):
        """Scroll the page to load more results."""
        try:
            # Get initial height
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            while True:
                # Scroll down with random steps
                current_height = 0
                while current_height < last_height:
                    step = random.randint(300, 500)
                    current_height = min(current_height + step, last_height)
                    self.driver.execute_script(f"window.scrollTo(0, {current_height});")
                    time.sleep(random.uniform(0.3, 0.7))
                
                # Add random mouse movements
                actions = ActionChains(self.driver)
                for _ in range(random.randint(2, 4)):
                    actions.move_by_offset(
                        random.randint(-100, 100),
                        random.randint(-100, 100)
                    )
                    actions.pause(random.uniform(0.1, 0.3))
                actions.perform()
                
                # Wait for possible new content
                time.sleep(random.uniform(2, 4))
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                # Break if no more new content
                if new_height == last_height:
                    break
                    
                last_height = new_height
                
        except Exception as e:
            self.logger.error(f"Error while scrolling: {str(e)}")

    def _search_articles(self, query: str, start_date: str, end_date: str, source: str = None) -> List[Dict]:
        """Search Google News for articles from a specific source within date range."""
        articles = []
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                articles = self._search_source(source, query, start_date, end_date)
                break
                
            except Exception as e:
                self.logger.error(f"Error searching {source}: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    self.logger.info(f"Retrying... (attempt {retry_count + 1} of {max_retries})")
                    time.sleep(random.uniform(20, 40))  # Longer delay between retries
        
        return articles

    def _extract_articles(self):
        """Extract articles from the current page."""
        try:
            # Parse results
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            results = soup.find_all(class_="g")
            
            if not results:
                self.logger.warning("No results found in the page, might need to retry")
                return []
            
            articles = []
            for result in results:
                article = self._extract_article_info(result)
                if article and article['url'] not in self.processed_urls:
                    articles.append(article)
                    self.processed_urls.add(article['url'])
            
            self.logger.info(f"Found {len(articles)} articles")
            return articles
        
        except Exception as e:
            self.logger.error(f"Error extracting articles: {str(e)}")
            return []

    def run(self, query: str, start_date: str, end_date: str) -> List[Dict]:
        """Run the scraper for all sources."""
        all_articles = []
        
        self.logger.info(
            f"Starting Google News scraper for query '{query}' "
            f"from {start_date} to {end_date}"
        )
        
        # Generate weekly date ranges
        date_ranges = self._generate_weekly_ranges(start_date, end_date)
        self.logger.info(f"Generated {len(date_ranges)} weekly ranges")
        
        # Search each source for each week
        for source_domain, source_name in self.target_sources.items():
            for week_start, week_end in date_ranges:
                try:
                    articles = self._search_articles(query, week_start, week_end, source_domain)
                    all_articles.extend(articles)
                    
                    self.logger.info(
                        f"Completed {source_name} search for week {week_start} to {week_end}: "
                        f"{len(articles)} articles found"
                    )
                    
                    # Add random delay between weeks
                    time.sleep(self._get_random_delay())
                    
                except Exception as e:
                    self.logger.error(
                        f"Error searching {source_name} for week {week_start} to {week_end}: "
                        f"{str(e)}"
                    )
        
        self.logger.info(f"Total articles found across all sources: {len(all_articles)}")
        return all_articles

    def save_articles(self, articles: List[Dict], filename: str = None) -> str:
        """Save articles to a JSON file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"google_news_articles_{timestamp}.json"
        
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved {len(articles)} articles to {filepath}")
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
        
        self.logger.info(f"Saved {len(articles)} articles to {filepath}")
        return filepath
