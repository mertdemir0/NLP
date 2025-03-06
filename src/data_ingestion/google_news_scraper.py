"""Google Search scraper with advanced features.

This module provides a specialized scraper for Google Search that:
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
from urllib.parse import urljoin, urlparse, quote_plus, quote
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
import urllib.parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('google_search_scraping.log')
    ]
)

class GoogleSearchScraper:
    """Advanced Google Search scraper with anti-detection and comprehensive coverage."""
    
    def __init__(self, 
                 headless: bool = True,
                 use_proxy: bool = False,
                 max_workers: int = 3,
                 data_dir: str = 'data/google_search',
                 delay_range: Tuple[float, float] = (2.0, 5.0)):
        """Initialize the Google Search scraper.
        
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
        """Format date for Google Search URL."""
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
        """Build Google Search URL with date range and optional source filter."""
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
        """Extract article information from a Google Search result element."""
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
            
            # Navigate to Google Search
            self._safe_get("https://www.google.com")
            time.sleep(random.uniform(3, 5))
            
            # Find and interact with search box using multiple selectors
            search_selectors = [
                (By.NAME, "q"),
                (By.CSS_SELECTOR, "input[type='text']"),
                (By.CSS_SELECTOR, "input[title='Search']")
            ]
            
            search_box = None
            for by, selector in search_selectors:
                try:
                    search_box = self._wait_and_find_element(by, selector, timeout=10)
                    if search_box:
                        break
                except:
                    continue
                    
            if not search_box:
                raise Exception("Could not find search box")
            
            # Clear and type with human-like behavior
            search_box.clear()
            time.sleep(random.uniform(1, 2))
            
            # Type query with site filter
            self._human_type(search_box, f"site:{source} {query}")
            search_box.send_keys(Keys.RETURN)
            time.sleep(random.uniform(3, 5))
            
            # Click News tab using multiple strategies
            news_selectors = [
                "//a[contains(@href, '/news') and contains(text(), 'News')]",
                "//a[contains(@href, '/news') and .//span[contains(text(), 'News')]]",
                "//div[@role='navigation']//a[contains(@href, '/news')]",
                "//div[contains(@class, 'hdtb-mitem')]//a[contains(@href, '/news')]"
            ]
            
            for selector in news_selectors:
                try:
                    news_tab = self._wait_and_find_element(By.XPATH, selector, timeout=10)
                    if news_tab:
                        self._human_click(news_tab)
                        time.sleep(random.uniform(2, 4))
                        break
                except:
                    continue
            
            # Click Tools using multiple strategies
            tools_selectors = [
                "//div[text()='Tools']",
                "//div[@aria-label='Tools']",
                "//span[text()='Tools']",
                "//div[contains(@class, 'hdtb-mitem')][contains(., 'Tools')]"
            ]
            
            for selector in tools_selectors:
                try:
                    tools_button = self._wait_and_find_element(By.XPATH, selector, timeout=10)
                    if tools_button:
                        self._human_click(tools_button)
                        time.sleep(random.uniform(2, 3))
                        break
                except:
                    continue
            
            # Click Any time dropdown using multiple strategies
            time_selectors = [
                "//div[contains(@class, 'hdtb-mn-hd')][.//span[contains(text(), 'Any time')]]",
                "//g-popup[contains(@class, 'timerange')]//span[contains(text(), 'Any time')]",
                "//div[@aria-label='Time']",
                "//div[contains(@class, 'KTBKoe')]"
            ]
            
            for selector in time_selectors:
                try:
                    time_dropdown = self._wait_and_find_element(By.XPATH, selector, timeout=10)
                    if time_dropdown:
                        self._human_click(time_dropdown)
                        time.sleep(random.uniform(2, 3))
                        break
                except:
                    continue
            
            # Click Custom range using multiple strategies
            custom_selectors = [
                "//div[contains(@class, 'y0fQ9c')][contains(., 'Custom range')]",
                "//g-menu-item[contains(., 'Custom range')]",
                "//div[@role='menuitem'][contains(., 'Custom range')]"
            ]
            
            for selector in custom_selectors:
                try:
                    custom_range = self._wait_and_find_element(By.XPATH, selector, timeout=10)
                    if custom_range:
                        self._human_click(custom_range)
                        time.sleep(random.uniform(2, 3))
                        break
                except:
                    continue
            
            # Input date range using multiple strategies
            date_input_selectors = [
                ("input#OouJcb", "input#rzG2be"),
                ("input[aria-label*='Start date']", "input[aria-label*='End date']"),
                ("input.cEZxRc", "input.WZvVqe")
            ]
            
            start_input = end_input = None
            for start_sel, end_sel in date_input_selectors:
                try:
                    start_input = self._wait_and_find_element(By.CSS_SELECTOR, start_sel, timeout=10)
                    end_input = self._wait_and_find_element(By.CSS_SELECTOR, end_sel, timeout=10)
                    if start_input and end_input:
                        break
                except:
                    continue
                    
            if not (start_input and end_input):
                raise Exception("Could not find date input fields")
            
            # Clear and input dates with human-like behavior
            for input_field in [start_input, end_input]:
                input_field.clear()
                time.sleep(random.uniform(0.5, 1))
            
            self._human_type(start_input, start_date)
            time.sleep(random.uniform(1, 2))
            self._human_type(end_input, end_date)
            time.sleep(random.uniform(1, 2))
            
            # Click Go button using multiple strategies
            go_selectors = [
                "//button[contains(., 'Go')]",
                "//g-button[contains(., 'Go')]",
                "//div[@role='button'][contains(., 'Go')]",
                "//span[contains(@class, 'z1asCe')][contains(., 'Go')]"
            ]
            
            for selector in go_selectors:
                try:
                    go_button = self._wait_and_find_element(By.XPATH, selector, timeout=10)
                    if go_button:
                        self._human_click(go_button)
                        time.sleep(random.uniform(3, 5))
                        break
                except:
                    continue
            
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

    def _extract_articles(self):
        """Extract articles from the current page."""
        articles = []
        try:
            # Multiple selectors for article containers
            article_selectors = [
                "div.SoaBEf",  # Primary Google News selector
                "div.WlydOe",  # Alternative container
                "div[role='article']",  # Role-based selector
                "div.g",  # Generic Google result
                "div.xuvV6b",  # Another news container
            ]
            
            article_elements = []
            for selector in article_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        article_elements.extend(elements)
                        break
                except:
                    continue
                    
            if not article_elements:
                self.logger.warning("No article elements found with primary selectors")
                # Fallback to any div containing an article-like structure
                article_elements = self.driver.find_elements(
                    By.XPATH,
                    "//div[.//a[contains(@href, 'http') or contains(@href, 'https')] and .//h3]"
                )
            
            for article in article_elements:
                try:
                    # Multiple selectors for title
                    title_selectors = [
                        ".//h3[contains(@class, 'r')]/a",
                        ".//h3/a",
                        ".//a[contains(@class, 'DY5T1d')]",
                        ".//div[contains(@class, 'vvjwJb')]//a",
                        ".//a[contains(@class, 'WlydOe')]"
                    ]
                    
                    title_element = None
                    title_text = ""
                    for selector in title_selectors:
                        try:
                            title_element = article.find_element(By.XPATH, selector)
                            if title_element:
                                title_text = title_element.text.strip()
                                if title_text:
                                    break
                        except:
                            continue
                    
                    if not title_text:
                        # Fallback to any h3 or strong text
                        try:
                            title_element = article.find_element(By.XPATH, ".//h3 | .//strong")
                            title_text = title_element.text.strip()
                        except:
                            continue
                    
                    # Multiple selectors for URL
                    url_selectors = [
                        ".//a[contains(@class, 'WlydOe')]",
                        ".//h3/a",
                        ".//a[contains(@href, 'http')]",
                        ".//a[contains(@class, 'VDXfz')]"
                    ]
                    
                    url = ""
                    for selector in url_selectors:
                        try:
                            url_element = article.find_element(By.XPATH, selector)
                            if url_element:
                                url = url_element.get_attribute("href")
                                if url and ("http" in url or "https" in url):
                                    break
                        except:
                            continue
                            
                    if not url:
                        continue
                        
                    # Clean URL by removing Google redirects
                    url = self._clean_url(url)
                    
                    # Multiple selectors for snippet
                    snippet_selectors = [
                        ".//div[contains(@class, 'VwiC3b')]",
                        ".//div[contains(@class, 'st')]",
                        ".//div[@class='snipp']",
                        ".//div[contains(@style, 'color')]"
                    ]
                    
                    snippet = ""
                    for selector in snippet_selectors:
                        try:
                            snippet_element = article.find_element(By.XPATH, selector)
                            if snippet_element:
                                snippet = snippet_element.text.strip()
                                if snippet:
                                    break
                        except:
                            continue
                            
                    # Multiple selectors for date
                    date_selectors = [
                        ".//time",
                        ".//span[contains(@class, 'WG9SHc')]",
                        ".//div[contains(@class, 'OSrXXb')]",
                        ".//span[contains(text(), ' ago')]"
                    ]
                    
                    date = ""
                    for selector in date_selectors:
                        try:
                            date_element = article.find_element(By.XPATH, selector)
                            if date_element:
                                date = date_element.text.strip()
                                if date:
                                    break
                        except:
                            continue
                    
                    # Only add article if we have at least title and URL
                    if title_text and url:
                        article_data = {
                            'title': title_text,
                            'url': url,
                            'snippet': snippet,
                            'date': date
                        }
                        articles.append(article_data)
                        
                except Exception as e:
                    self.logger.warning(f"Error extracting article data: {str(e)}")
                    continue
            
            self.logger.info(f"Extracted {len(articles)} articles")
            
        except Exception as e:
            self.logger.error(f"Error during article extraction: {str(e)}")
            
        return articles
        
    def _clean_url(self, url: str) -> str:
        """Clean Google redirect URLs to get the actual article URL."""
        try:
            # Handle Google redirect URLs
            if "/url?" in url:
                parsed = urllib.parse.urlparse(url)
                query_params = urllib.parse.parse_qs(parsed.query)
                if 'url' in query_params:
                    return query_params['url'][0]
                elif 'q' in query_params:
                    return query_params['q'][0]
            return url
        except:
            return url

    def _search_articles(self, query: str, start_date: str, end_date: str, source: str = None) -> List[Dict]:
        """Search Google Search for articles from a specific source within date range."""
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

    def run(self, query: str, start_date: str, end_date: str) -> List[Dict]:
        """Run the scraper for all sources."""
        all_articles = []
        
        self.logger.info(
            f"Starting Google Search scraper for query '{query}' "
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
            filename = f"google_search_articles_{timestamp}.json"
        
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved {len(articles)} articles to {filepath}")
        return filepath
    
    def save_to_csv(self, articles: List[Dict], filename: str = None) -> str:
        """Save articles to a CSV file."""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"google_search_articles_{timestamp}.csv"
        
        filepath = os.path.join(self.data_dir, filename)
        
        # Convert to DataFrame and save
        df = pd.DataFrame(articles)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        self.logger.info(f"Saved {len(articles)} articles to {filepath}")
        return filepath
