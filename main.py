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

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

# Lua script for Splash to execute
SEARCH_SCRIPT = """
function main(splash, args)
    -- Set user agent
    splash:set_user_agent(args.user_agent)
    
    -- Set custom headers
    splash:on_request(function(request)
        request:set_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        request:set_header('Accept-Language', 'en-US,en;q=0.5')
    end)
    
    -- Load page
    assert(splash:go(args.url))
    splash:wait(5)
    
    -- Scroll down slowly
    splash:evaljs("window.scrollTo(0, document.body.scrollHeight/4)")
    splash:wait(2)
    
    return {
        html = splash:html(),
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
        'DOWNLOAD_DELAY': 30,  # 30 seconds delay between requests
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
        self.max_results = 20  # Reduced maximum results per day

    def start_requests(self):
        base_url = "https://www.google.com/search"
        query = f'site:bloomberg.com intitle:nuclear "{self.date}"'
        url = f"{base_url}?q={quote(query)}&num=20"
        
        yield SplashRequest(
            url,
            callback=self.parse_search_results,
            endpoint='execute',
            args={
                'lua_source': SEARCH_SCRIPT,
                'user_agent': random.choice(USER_AGENTS),
                'wait': 5,
            },
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
                delay = random.uniform(30, 45)  # Random delay between pages
                logging.info(f"Waiting {delay:.1f} seconds before next page...")
                time.sleep(delay)
                
                yield SplashRequest(
                    response.urljoin(next_page),
                    callback=self.parse_search_results,
                    endpoint='execute',
                    args={
                        'lua_source': SEARCH_SCRIPT,
                        'user_agent': random.choice(USER_AGENTS),
                        'wait': 5,
                    },
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
                'DOWNLOAD_TIMEOUT': 90,
            })
            
            process.crawl(GoogleSearchSpider, date=date)
            process.start()
            
            # Force a reset of the crawler process
            process.stop()
            
            # Add random delay between days
            delay = random.uniform(120, 180)  # Random delay between 2-3 minutes
            logging.info(f"Waiting {delay:.1f} seconds before next day...")
            time.sleep(delay)
            
    except Exception as e:
        logging.error(f"Error during execution: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()