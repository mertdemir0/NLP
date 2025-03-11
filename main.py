import scrapy
from scrapy_splash import SplashRequest
from scrapy.crawler import CrawlerProcess
from scrapy.spiders import Spider
from datetime import datetime, timedelta
import sqlite3
import logging
import time
from urllib.parse import urlparse, quote
import json
from typing import List, Dict, Any
import random
import requests
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

<<<<<<< HEAD
def get_free_proxies() -> List[str]:
    """Get a list of free proxies"""
    proxies = []
    try:
        # Get proxies from free-proxy-list.net
        response = requests.get('https://free-proxy-list.net/')
        soup = BeautifulSoup(response.text, 'html.parser')
        proxy_table = soup.find('table')
        
        if proxy_table:
            for row in proxy_table.find_all('tr')[1:]:  # Skip header
                cols = row.find_all('td')
                if len(cols) >= 7:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    https = cols[6].text.strip()
                    if https == 'yes':
                        proxy = f'http://{ip}:{port}'
                        proxies.append(proxy)
        
        logging.info(f"Found {len(proxies)} free proxies")
        return proxies[:10]  # Return top 10 proxies
    except Exception as e:
        logging.error(f"Error getting proxies: {str(e)}")
        return []

=======
>>>>>>> cadf26e66014e9c102aafaf822da77ec56712ead
# Lua script for Splash to execute
SEARCH_SCRIPT = """
function main(splash, args)
    splash:set_user_agent(args.user_agent)
    
<<<<<<< HEAD
    -- Set custom headers
=======
>>>>>>> cadf26e66014e9c102aafaf822da77ec56712ead
    splash:on_request(function(request)
        request:set_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        request:set_header('Accept-Language', 'en-US,en;q=0.5')
    end)
    
<<<<<<< HEAD
    -- Set proxy if provided
    if args.proxy then
        splash:on_request(function(request)
            request:set_proxy{
                host = args.proxy_host,
                port = args.proxy_port,
                type = 'HTTP'
            }
        end)
    end
    
    -- Randomize viewport size
    local width = math.random(1024, 1920)
    local height = math.random(768, 1080)
    splash:set_viewport_size(width, height)
    
    -- Load page with retry
    local ok, reason
    for retry=1,3 do
        ok, reason = splash:go(args.url)
        if ok then break end
        splash:wait(2)
    end
    
    if not ok then
        return {error = reason}
    end
    
    -- Random initial wait
    splash:wait(math.random(4, 7))
    
    -- Scroll down slowly to simulate human behavior
    for i=1,4 do
        splash:evaljs(string.format("window.scrollTo(0, %d)", i * document.body.scrollHeight/4))
        splash:wait(math.random(1, 2))
    end
    
    -- Scroll back up randomly
    splash:evaljs(string.format("window.scrollTo(0, %d)", math.random(0, document.body.scrollHeight/2)))
    splash:wait(math.random(1, 2))
=======
    assert(splash:go(args.url))
    splash:wait(5)
    
    -- Scroll down a bit to simulate human behavior
    splash:evaljs("window.scrollTo(0, document.body.scrollHeight/4)")
    splash:wait(1)
>>>>>>> cadf26e66014e9c102aafaf822da77ec56712ead
    
    return {
        html = splash:html(),
        url = splash:url(),
        cookies = splash:get_cookies()
    }
end
"""

# List of user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
]

class GoogleSearchSpider(Spider):
    name = 'google_search'
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
<<<<<<< HEAD
        'DOWNLOAD_DELAY': 30,  # 30 seconds delay between requests
=======
        'DOWNLOAD_DELAY': 20,  # 20 seconds delay between requests
>>>>>>> cadf26e66014e9c102aafaf822da77ec56712ead
        'CONCURRENT_REQUESTS': 1,  # Only one request at a time
        'COOKIES_ENABLED': True,
        'SPLASH_URL': 'http://localhost:8050',
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'SPIDER_MIDDLEWARES': {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter',
    }

    def __init__(self, date: str = None, *args, **kwargs):
        super(GoogleSearchSpider, self).__init__(*args, **kwargs)
        self.date = date
        self.conn = init_database()
        self.results_count = 0
<<<<<<< HEAD
        self.max_results = 20  # Further reduced maximum results per day
        self.proxies = get_free_proxies()
        self.current_proxy_index = 0

    def get_next_proxy(self) -> Dict[str, str]:
        """Get next proxy from the pool"""
        if not self.proxies:
            return None
            
        proxy = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        try:
            # Parse proxy URL
            proxy_parts = proxy.split('://')[-1].split(':')
            return {
                'host': proxy_parts[0],
                'port': int(proxy_parts[1])
            }
        except:
            return None
=======
        self.max_results = 30  # Reduced maximum results per day to avoid detection
>>>>>>> cadf26e66014e9c102aafaf822da77ec56712ead

    def start_requests(self):
        base_url = "https://www.google.com/search"
        query = f'site:bloomberg.com intitle:nuclear "{self.date}"'
<<<<<<< HEAD
        url = f"{base_url}?q={quote(query)}&num=20"
        
        proxy_info = self.get_next_proxy()
        splash_args = {
            'lua_source': SEARCH_SCRIPT,
            'user_agent': random.choice(USER_AGENTS),
            'wait': 5,
        }
        
        if proxy_info:
            splash_args.update({
                'proxy': True,
                'proxy_host': proxy_info['host'],
                'proxy_port': proxy_info['port']
            })
        
=======
        url = f"{base_url}?q={quote(query)}&num=30"
        
>>>>>>> cadf26e66014e9c102aafaf822da77ec56712ead
        yield SplashRequest(
            url,
            callback=self.parse_search_results,
            endpoint='execute',
<<<<<<< HEAD
            args=splash_args,
=======
            args={
                'lua_source': SEARCH_SCRIPT,
                'user_agent': random.choice(USER_AGENTS),
                'wait': 5,
            },
>>>>>>> cadf26e66014e9c102aafaf822da77ec56712ead
            meta={'page': 1}
        )

    def parse_search_results(self, response):
        # Extract all search result links
        for result in response.css('div.g'):
            if self.results_count >= self.max_results:
                return

            link = result.css('a::attr(href)').get()
            if link and 'bloomberg.com' in link and self.is_valid_bloomberg_url(link):
                self.results_count += 1
                self.save_to_db(link)
                logging.info(f"Found article: {link}")

        # Check if there's a next page and we haven't reached the limit
        if self.results_count < self.max_results:
            next_page = response.css('a#pnnext::attr(href)').get()
            if next_page:
<<<<<<< HEAD
                delay = random.uniform(30, 45)  # Longer random delay between pages
                logging.info(f"Waiting {delay:.1f} seconds before next page...")
                time.sleep(delay)
                
                proxy_info = self.get_next_proxy()
                splash_args = {
                    'lua_source': SEARCH_SCRIPT,
                    'user_agent': random.choice(USER_AGENTS),
                    'wait': 5,
                }
                
                if proxy_info:
                    splash_args.update({
                        'proxy': True,
                        'proxy_host': proxy_info['host'],
                        'proxy_port': proxy_info['port']
                    })
                
=======
                delay = random.uniform(20, 30)  # Random delay between pages
                logging.info(f"Waiting {delay:.1f} seconds before next page...")
                time.sleep(delay)
                
>>>>>>> cadf26e66014e9c102aafaf822da77ec56712ead
                yield SplashRequest(
                    response.urljoin(next_page),
                    callback=self.parse_search_results,
                    endpoint='execute',
<<<<<<< HEAD
                    args=splash_args,
=======
                    args={
                        'lua_source': SEARCH_SCRIPT,
                        'user_agent': random.choice(USER_AGENTS),
                        'wait': 5,
                    },
>>>>>>> cadf26e66014e9c102aafaf822da77ec56712ead
                    meta={'page': response.meta['page'] + 1}
                )

    def is_valid_bloomberg_url(self, url: str) -> bool:
        """Check if URL is a valid Bloomberg article URL"""
        try:
            parsed = urlparse(url)
            return (parsed.netloc.endswith('bloomberg.com') and 
                    not any(x in url.lower() for x in ['/videos/', '/audio/', '/podcasts/']))
        except:
            return False

    def save_to_db(self, url: str):
        """Save URL to database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO scrapy_articles 
                (url, fetch_date, created_at)
                VALUES (?, ?, datetime('now'))
            ''', (url, self.date))
            self.conn.commit()
            logging.info(f"Added: {url}")
        except Exception as e:
            logging.error(f"Error saving URL {url}: {str(e)}")

    def closed(self, reason):
        if self.conn:
            self.conn.close()

def init_database() -> sqlite3.Connection:
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('nuclear_news.db')
    c = conn.cursor()
    
    # Create new table for Scrapy results
    c.execute('''CREATE TABLE IF NOT EXISTS scrapy_articles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  url TEXT,
                  fetch_date TEXT,
                  created_at TIMESTAMP,
                  content TEXT,
                  title TEXT,
                  processed BOOLEAN DEFAULT 0)''')
    
    conn.commit()
    return conn

def generate_date_range(start_date: str, end_date: str) -> List[str]:
    """Generate a list of dates between start and end date"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return dates

def main():
    START_DATE = '2020-01-01'
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    
    # Initialize database
    conn = init_database()
    
    try:
        # Get daily dates
        dates = generate_date_range(START_DATE, END_DATE)
        total_days = len(dates)
        
        logging.info(f"Starting collection for {total_days} days from {START_DATE} to {END_DATE}")
        
        # Process each day
        for idx, date in enumerate(dates, 1):
            logging.info(f"\nProcessing date: {date} ({idx}/{total_days})")
            
            process = CrawlerProcess({
                'LOG_LEVEL': 'INFO',
                'COOKIES_ENABLED': True,
                'RETRY_TIMES': 3,
<<<<<<< HEAD
                'DOWNLOAD_TIMEOUT': 90,
=======
                'DOWNLOAD_TIMEOUT': 60,
>>>>>>> cadf26e66014e9c102aafaf822da77ec56712ead
            })
            
            process.crawl(GoogleSearchSpider, date=date)
            process.start()
            
            # Force a reset of the crawler process
            process.stop()
            
            # Add random delay between days
<<<<<<< HEAD
            delay = random.uniform(120, 180)  # Random delay between 2-3 minutes
=======
            delay = random.uniform(90, 120)  # Random delay between 1.5-2 minutes
>>>>>>> cadf26e66014e9c102aafaf822da77ec56712ead
            logging.info(f"Waiting {delay:.1f} seconds before next day...")
            time.sleep(delay)
            
    except Exception as e:
        logging.error(f"Error during execution: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()