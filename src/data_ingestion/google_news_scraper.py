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
                "//form[@action='/sorry']",
                "//div[contains(text(), 'unusual traffic')]",
                "//div[contains(text(), 'verify you are human')]"
            ]
            
            for selector in captcha_selectors:
                if driver.find_elements(By.XPATH, selector):
                    logger.warning("Captcha detected! Implementing bypass strategy...")
                    
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
                    logger.warning("Failed to solve captcha automatically")
                    return False
            
            # No captcha detected
            return True
            
        except Exception as e:
            logger.error(f"Error handling captcha: {str(e)}")
            return False

    def _search_source(self, source: str, query: str, start_date: str, end_date: str):
        """Search for articles from a specific source within date range."""
        try:
            logger.info(f"Searching {source} articles for '{query}' from {start_date} to {end_date}")
            
            # Enhanced wait strategy
            wait = WebDriverWait(self.driver, 20, poll_frequency=1)
            
            # Navigate to Google News
            self._safe_get("https://news.google.com")
            time.sleep(random.uniform(2, 4))
            
            # Wait for and click search button
            search_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "gb_Ue")))
            self._human_click(search_button)
            
            # Wait for search box and type query
            search_box = wait.until(EC.presence_of_element_located((By.NAME, "q")))
            self._human_type(search_box, f"site:{source} {query}")
            search_box.send_keys(Keys.RETURN)
            
            # Wait for Tools button and click
            tools_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Tools')]")))
            self._human_click(tools_button)
            time.sleep(random.uniform(1, 2))
            
            # Wait for and click date filter
            date_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'hdtb-mn-hd') and contains(., 'Any time')]")))
            self._human_click(date_button)
            time.sleep(random.uniform(1, 2))
            
            # Wait for and click custom range
            custom_range = wait.until(EC.element_to_be_clickable((By.XPATH, "//g-menu-item[contains(., 'Custom range...')]")))
            self._human_click(custom_range)
            time.sleep(random.uniform(1, 2))
            
            # Enhanced date input handling
            start_input = wait.until(EC.presence_of_element_located((By.ID, "OouJcb")))
            end_input = wait.until(EC.presence_of_element_located((By.ID, "rzG2be")))
            
            # Clear existing dates
            start_input.clear()
            time.sleep(random.uniform(0.5, 1))
            end_input.clear()
            time.sleep(random.uniform(0.5, 1))
            
            # Input dates
            self._human_type(start_input, start_date)
            time.sleep(random.uniform(0.5, 1))
            self._human_type(end_input, end_date)
            
            # Click go button
            go_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//g-button[contains(., 'Go')]")))
            self._human_click(go_button)
            
            # Wait for results to load
            time.sleep(random.uniform(3, 5))
            
            # Extract and return results
            return self._extract_articles()
            
        except Exception as e:
            logger.error(f"Error searching {source}: {str(e)}")
            if "element not interactable" in str(e):
                logger.info("Page elements not ready, increasing wait time")
                time.sleep(random.uniform(5, 8))
            raise

    def _search_articles(self, query: str, start_date: str, end_date: str, source: str = None) -> List[Dict]:
        """Search Google News for articles from a specific source within date range."""
        logger.info(f"Searching {source} articles for '{query}' from {start_date} to {end_date}")
        
        articles = []
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            driver = None
            try:
                # Build search URL
                url = self._build_search_url(query, start_date, end_date, source)
                
                # Initialize driver with new profile each time
                driver = self._setup_driver()
                
                # First visit Google homepage and wait
                driver.get("https://www.google.com")
                time.sleep(random.uniform(3, 5))
                
                # Perform some random searches first
                random_searches = [
                    "weather today",
                    "latest news",
                    "current events"
                ]
                for search in random_searches[:random.randint(1, 2)]:
                    search_box = driver.find_element(By.NAME, "q")
                    search_box.clear()
                    # Type like a human with random delays
                    for char in search:
                        search_box.send_keys(char)
                        time.sleep(random.uniform(0.1, 0.3))
                    search_box.send_keys(Keys.RETURN)
                    time.sleep(random.uniform(2, 4))
                
                # Now navigate to the actual search URL
                driver.get(url)
                time.sleep(random.uniform(3, 5))
                
                # Handle captcha if present
                if not self._handle_captcha(driver):
                    logger.warning("Captcha detected, retrying with new session...")
                    retry_count += 1
                    time.sleep(random.uniform(30, 60))  # Longer wait before retry
                    continue
                
                # Wait for search results with a longer timeout
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "g"))
                    )
                except TimeoutException:
                    logger.warning("No results found, might be blocked. Retrying...")
                    retry_count += 1
                    time.sleep(random.uniform(20, 40))  # Longer wait before retry
                    continue
                
                # Add some random mouse movements and scrolling
                actions = ActionChains(driver)
                for _ in range(3):
                    actions.move_by_offset(random.randint(-100, 100), random.randint(-100, 100))
                    actions.pause(random.uniform(0.1, 0.3))
                actions.perform()
                
                # Scroll slowly to load all results
                screen_heights = driver.execute_script("return Math.max( document.body.scrollHeight, document.body.offsetHeight, document.documentElement.clientHeight, document.documentElement.scrollHeight, document.documentElement.offsetHeight);")
                current_position = 0
                step = random.randint(300, 500)  # Random step size
                
                while current_position < screen_heights:
                    current_position = min(current_position + step, screen_heights)
                    driver.execute_script(f"window.scrollTo(0, {current_position});")
                    time.sleep(random.uniform(0.5, 1.0))  # Random delay while scrolling
                
                # Parse results
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                results = soup.find_all(class_="g")
                
                if not results:
                    logger.warning("No results found in the page, might need to retry")
                    retry_count += 1
                    time.sleep(random.uniform(15, 30))  # Longer wait before retry
                    continue
                
                for result in results:
                    article = self._extract_article_info(result)
                    if article and article['url'] not in self.processed_urls:
                        articles.append(article)
                        self.processed_urls.add(article['url'])
                
                logger.info(f"Found {len(articles)} articles from {source}")
                
                # If we got here successfully, break the retry loop
                break
                
            except Exception as e:
                logger.error(f"Error searching {source}: {str(e)}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying... (attempt {retry_count + 1} of {max_retries})")
                    time.sleep(random.uniform(20, 40))  # Longer delay between retries
                
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
        
        return articles

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
                    
                    articles = self._search_source(source_domain, query, week_start, week_end)
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
