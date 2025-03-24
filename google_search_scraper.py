import os
import json
import time
import random
import logging
from datetime import datetime
from urllib.parse import quote_plus, urlparse, parse_qs
from typing import List, Dict, Any, Optional, Union

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("google_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("GoogleSearchScraper")

class GoogleSearchResult:
    """Class to represent a single Google search result"""
    
    def __init__(
        self, 
        title: str = "", 
        url: str = "", 
        displayed_url: str = "",
        snippet: str = "", 
        position: int = 0,
        featured: bool = False,
        is_ad: bool = False,
        is_video: bool = False,
        is_news: bool = False,
        extra_data: Dict[str, Any] = None
    ):
        self.title = title
        self.url = url
        self.displayed_url = displayed_url
        self.snippet = snippet
        self.position = position
        self.featured = featured
        self.is_ad = is_ad
        self.is_video = is_video
        self.is_news = is_news
        self.extra_data = extra_data or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a dictionary"""
        return {
            "title": self.title,
            "url": self.url,
            "displayed_url": self.displayed_url,
            "snippet": self.snippet,
            "position": self.position,
            "featured": self.featured,
            "is_ad": self.is_ad,
            "is_video": self.is_video,
            "is_news": self.is_news,
            "extra_data": self.extra_data,
            "timestamp": self.timestamp
        }

class GoogleSearchScraper:
    """
    A class to scrape Google search results using different methods
    """
    
    def __init__(
        self,
        method: str = "requests",
        headless: bool = True,
        proxy: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 5,
        random_delay: bool = True,
        user_agent: Optional[str] = None,
        cache_dir: Optional[str] = None,
        verbose: bool = False
    ):
        """
        Initialize the Google Search Scraper
        
        Args:
            method (str): Scraping method - "requests" or "selenium"
            headless (bool): Whether to run the browser in headless mode (selenium only)
            proxy (str): Proxy to use for requests (format: "http://user:pass@host:port")
            timeout (int): Request timeout in seconds
            max_retries (int): Maximum number of retries for failed requests
            retry_delay (int): Delay between retries in seconds
            random_delay (bool): Whether to add random delay between requests
            user_agent (str): Custom user agent string (if None, a random one is generated)
            cache_dir (str): Directory to cache results (if None, caching is disabled)
            verbose (bool): Whether to print verbose output
        """
        self.method = method.lower()
        self.headless = headless
        self.proxy = proxy
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.random_delay = random_delay
        self.verbose = verbose
        
        # Set up user agent
        if user_agent is None:
            try:
                self.user_agent = UserAgent().random
            except Exception:
                # Fallback to a common user agent if fake_useragent fails
                self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        else:
            self.user_agent = user_agent
            
        # Set up caching
        self.cache_dir = cache_dir
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
            
        # Initialize browser for selenium method
        self.driver = None
        if self.method == "selenium":
            self._init_selenium()
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver"""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless=new")
            
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"user-agent={self.user_agent}")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            
            if self.proxy:
                chrome_options.add_argument(f"--proxy-server={self.proxy}")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set window size
            self.driver.set_window_size(1920, 1080)
            
            # Execute CDP commands to prevent detection
            self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": self.user_agent
            })
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                """
            })
            
            logger.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {e}")
            raise
    
    def _get_cache_path(self, query: str, num_results: int, language: str, country: str) -> str:
        """Generate a cache file path for the given search parameters"""
        if not self.cache_dir:
            return None
            
        safe_query = "".join(c if c.isalnum() else "_" for c in query)
        cache_file = f"{safe_query}_{num_results}_{language}_{country}.json"
        return os.path.join(self.cache_dir, cache_file)
    
    def _load_from_cache(self, cache_path: str) -> Optional[List[Dict[str, Any]]]:
        """Load search results from cache if available and not expired"""
        if not cache_path or not os.path.exists(cache_path):
            return None
            
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                
            # Check if cache is expired (older than 24 hours)
            cache_time = datetime.fromisoformat(cache_data.get("timestamp", "2000-01-01T00:00:00"))
            if (datetime.now() - cache_time).total_seconds() > 86400:  # 24 hours
                return None
                
            return cache_data.get("results", [])
        except Exception as e:
            logger.warning(f"Failed to load from cache: {e}")
            return None
    
    def _save_to_cache(self, cache_path: str, results: List[GoogleSearchResult], query: str) -> None:
        """Save search results to cache"""
        if not cache_path:
            return
            
        try:
            cache_data = {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "results": [result.to_dict() for result in results]
            }
            
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"Saved results to cache: {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save to cache: {e}")
    
    def search(
        self, 
        query: str, 
        num_results: int = 10, 
        language: str = "en", 
        country: str = "us",
        page: int = 1,
        safe_search: bool = True,
        time_period: Optional[str] = None,
        site_search: Optional[str] = None
    ) -> List[GoogleSearchResult]:
        """
        Perform a Google search and extract results
        
        Args:
            query (str): The search query
            num_results (int): Number of results to extract
            language (str): Language code for search (e.g., "en")
            country (str): Country code for search (e.g., "us")
            page (int): Page number to scrape (1-based)
            safe_search (bool): Whether to enable safe search
            time_period (str): Time period for results (e.g., "day", "week", "month", "year")
            site_search (str): Limit search to specific site (e.g., "example.com")
            
        Returns:
            list: List of GoogleSearchResult objects
        """
        # Check cache first
        cache_path = self._get_cache_path(query, num_results, language, country)
        cached_results = self._load_from_cache(cache_path)
        if cached_results:
            logger.info(f"Loaded {len(cached_results)} results from cache")
            return [GoogleSearchResult(**result) for result in cached_results]
        
        # Construct the search query
        search_query = query
        if site_search:
            search_query = f"site:{site_search} {search_query}"
        
        # Construct Google search URL
        encoded_query = quote_plus(search_query)
        url = f"https://www.google.com/search?q={encoded_query}&hl={language}&gl={country}&num={num_results}"
        
        # Add pagination
        if page > 1:
            start = (page - 1) * 10
            url += f"&start={start}"
        
        # Add safe search
        if safe_search:
            url += "&safe=active"
        
        # Add time period
        if time_period:
            time_map = {
                "day": "d",
                "week": "w",
                "month": "m",
                "year": "y"
            }
            if time_period.lower() in time_map:
                url += f"&tbs=qdr:{time_map[time_period.lower()]}"
        
        # Choose scraping method
        if self.method == "selenium":
            results = self._search_with_selenium(url)
        else:  # Default to requests
            results = self._search_with_requests(url)
        
        # Save to cache
        self._save_to_cache(cache_path, results, query)
        
        return results
    
    def _search_with_requests(self, url: str) -> List[GoogleSearchResult]:
        """
        Perform a Google search using requests and BeautifulSoup
        
        Args:
            url (str): The Google search URL
            
        Returns:
            list: List of GoogleSearchResult objects
        """
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        
        proxies = None
        if self.proxy:
            proxies = {
                "http": self.proxy,
                "https": self.proxy
            }
        
        # Implement retry logic
        for attempt in range(self.max_retries):
            try:
                # Add random delay to avoid detection
                if self.random_delay and attempt > 0:
                    delay = self.retry_delay + random.uniform(1, 3)
                    logger.info(f"Waiting {delay:.2f} seconds before retry {attempt+1}/{self.max_retries}")
                    time.sleep(delay)
                
                response = requests.get(
                    url, 
                    headers=headers, 
                    proxies=proxies, 
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return self._parse_html(response.text)
                elif response.status_code == 429:
                    logger.warning(f"Rate limited (429). Retrying after delay...")
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.warning(f"HTTP error: {response.status_code}. Retrying...")
                    
            except requests.RequestException as e:
                logger.warning(f"Request failed: {e}. Attempt {attempt+1}/{self.max_retries}")
                if attempt == self.max_retries - 1:
                    logger.error(f"All retries failed: {e}")
                    raise
                time.sleep(self.retry_delay)
        
        return []
    
    def _search_with_selenium(self, url: str) -> List[GoogleSearchResult]:
        """
        Perform a Google search using Selenium
        
        Args:
            url (str): The Google search URL
            
        Returns:
            list: List of GoogleSearchResult objects
        """
        if not self.driver:
            self._init_selenium()
        
        try:
            # Navigate to the URL
            self.driver.get(url)
            
            # Wait for search results to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#search"))
            )
            
            # Add a small delay to ensure JavaScript has fully loaded
            time.sleep(2)
            
            # Get the page source and parse it
            html = self.driver.page_source
            return self._parse_html(html)
            
        except TimeoutException:
            logger.error("Timeout waiting for search results to load")
            return []
        except WebDriverException as e:
            logger.error(f"Selenium error: {e}")
            # Try to reinitialize the driver
            try:
                self.driver.quit()
            except:
                pass
            self._init_selenium()
            return []
    
    def _parse_html(self, html: str) -> List[GoogleSearchResult]:
        """
        Parse Google search results from HTML
        
        Args:
            html (str): The HTML content of the search results page
            
        Returns:
            list: List of GoogleSearchResult objects
        """
        results = []
        position = 0
        
        try:
            soup = BeautifulSoup(html, "lxml")
            
            # Check for CAPTCHA or other blocking mechanisms
            if "Our systems have detected unusual traffic from your computer network" in html:
                logger.warning("Google CAPTCHA detected. Try using a different IP or proxy.")
                return results
            
            # Find all search result containers
            # Main organic results
            organic_results = soup.select("div.g")
            
            for result in organic_results:
                position += 1
                try:
                    # Extract title
                    title_element = result.select_one("h3")
                    title = title_element.text.strip() if title_element else ""
                    
                    # Extract URL
                    link_element = result.select_one("a")
                    url = link_element.get("href", "") if link_element else ""
                    
                    # Clean URL (remove Google redirects)
                    if url.startswith("/url?"):
                        parsed_url = urlparse(url)
                        url_params = parse_qs(parsed_url.query)
                        if "q" in url_params:
                            url = url_params["q"][0]
                    
                    # Extract displayed URL
                    displayed_url_element = result.select_one("cite")
                    displayed_url = displayed_url_element.text.strip() if displayed_url_element else ""
                    
                    # Extract snippet
                    snippet_element = result.select_one("div.VwiC3b")
                    snippet = snippet_element.text.strip() if snippet_element else ""
                    
                    # Check if it's a featured result
                    featured = bool(result.select_one(".xpdopen"))
                    
                    # Check if it's a video result
                    is_video = bool(result.select_one("video-voyager"))
                    
                    # Check if it's a news result
                    is_news = bool(result.select_one("g-card"))
                    
                    # Create result object
                    search_result = GoogleSearchResult(
                        title=title,
                        url=url,
                        displayed_url=displayed_url,
                        snippet=snippet,
                        position=position,
                        featured=featured,
                        is_ad=False,  # Organic results are not ads
                        is_video=is_video,
                        is_news=is_news
                    )
                    
                    results.append(search_result)
                    
                except Exception as e:
                    logger.warning(f"Error parsing result {position}: {e}")
            
            # Check for ad results
            ad_results = soup.select("div.uEierd")
            for result in ad_results:
                position += 1
                try:
                    # Extract title
                    title_element = result.select_one("div.vvjwJb")
                    title = title_element.text.strip() if title_element else ""
                    
                    # Extract URL
                    link_element = result.select_one("a.sVXRqc")
                    url = link_element.get("href", "") if link_element else ""
                    
                    # Extract displayed URL
                    displayed_url_element = result.select_one("span.qzEoUe")
                    displayed_url = displayed_url_element.text.strip() if displayed_url_element else ""
                    
                    # Extract snippet
                    snippet_element = result.select_one("div.MUxGbd")
                    snippet = snippet_element.text.strip() if snippet_element else ""
                    
                    # Create result object
                    search_result = GoogleSearchResult(
                        title=title,
                        url=url,
                        displayed_url=displayed_url,
                        snippet=snippet,
                        position=position,
                        featured=False,
                        is_ad=True,
                        is_video=False,
                        is_news=False
                    )
                    
                    results.append(search_result)
                    
                except Exception as e:
                    logger.warning(f"Error parsing ad result {position}: {e}")
            
            # Extract featured snippets
            featured_snippet = soup.select_one("div.xpdopen")
            if featured_snippet:
                try:
                    # Extract title
                    title_element = featured_snippet.select_one("h3")
                    title = title_element.text.strip() if title_element else "Featured Snippet"
                    
                    # Extract URL
                    link_element = featured_snippet.select_one("a")
                    url = link_element.get("href", "") if link_element else ""
                    
                    # Clean URL
                    if url.startswith("/url?"):
                        parsed_url = urlparse(url)
                        url_params = parse_qs(parsed_url.query)
                        if "q" in url_params:
                            url = url_params["q"][0]
                    
                    # Extract displayed URL
                    displayed_url_element = featured_snippet.select_one("cite")
                    displayed_url = displayed_url_element.text.strip() if displayed_url_element else ""
                    
                    # Extract snippet
                    snippet_element = featured_snippet.select_one("div.hgKElc")
                    snippet = snippet_element.text.strip() if snippet_element else ""
                    
                    # Create result object
                    search_result = GoogleSearchResult(
                        title=title,
                        url=url,
                        displayed_url=displayed_url,
                        snippet=snippet,
                        position=0,  # Featured snippets are usually at position 0
                        featured=True,
                        is_ad=False,
                        is_video=False,
                        is_news=False,
                        extra_data={"type": "featured_snippet"}
                    )
                    
                    # Insert at the beginning
                    results.insert(0, search_result)
                    
                except Exception as e:
                    logger.warning(f"Error parsing featured snippet: {e}")
            
            logger.info(f"Extracted {len(results)} search results")
            return results
            
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return results
    
    def search_and_save(
        self, 
        query: str, 
        output_file: Optional[str] = None, 
        num_results: int = 10, 
        language: str = "en", 
        country: str = "us",
        **kwargs
    ) -> str:
        """
        Perform a Google search and save results to a JSON file
        
        Args:
            query (str): The search query
            output_file (str): Path to save the results (if None, generates a filename)
            num_results (int): Number of results to extract
            language (str): Language code for search
            country (str): Country code for search
            **kwargs: Additional arguments to pass to search()
            
        Returns:
            str: Path to the saved file
        """
        # Get search results
        results = self.search(
            query=query, 
            num_results=num_results, 
            language=language, 
            country=country,
            **kwargs
        )
        
        # Generate output filename if not provided
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_query = "".join(c if c.isalnum() else "_" for c in query)[:30]
            output_file = f"google_search_{safe_query}_{timestamp}.json"
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
        
        # Save results to JSON file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "num_results": len(results),
                "results": [result.to_dict() for result in results]
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Search results saved to {output_file}")
        return output_file
    
    def close(self):
        """Close the Selenium WebDriver if it's open"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """Example usage of the GoogleSearchScraper"""
    # Create an instance of GoogleSearchScraper
    scraper = GoogleSearchScraper(
        method="requests",  # Use "selenium" for JavaScript-heavy sites
        headless=True,
        random_delay=True,
        cache_dir="cache",
        verbose=True
    )
    
    try:
        # Example search query
        query = "python web scraping best practices"
        
        # Search and save results
        output_file = scraper.search_and_save(
            query=query,
            num_results=10,
            language="en",
            country="us",
            time_period="month"  # Get results from the past month
        )
        
        print(f"Results saved to {output_file}")
    finally:
        # Always close the scraper to release resources
        scraper.close()

if __name__ == "__main__":
    main() 