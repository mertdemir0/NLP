#!/usr/bin/env python
"""
Docker-compatible entry point for the NLP application.
This script imports and runs the main application with Docker-specific settings.
"""
import os
import sys
import logging
import random
from datetime import datetime
import sqlite3
from typing import List
import time
import traceback

# Import Docker configuration
from docker_config import (
    setup_signal_handlers, 
    get_db_path, 
    get_env, 
    get_env_int, 
    get_env_float
)

# Setup logging for Docker
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler()
    ]
)

# Import original functionality from main.py
# This allows us to reuse the code without modifying the original file
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import GoogleSearchSpider, generate_date_range, USER_AGENTS

# Setup signal handlers for Docker
setup_signal_handlers()

# Load custom Lua script if available
def get_lua_script():
    lua_path = get_env('LUA_SOURCE_PATH', None)
    if lua_path and os.path.exists(lua_path):
        logging.info(f"Loading custom Lua script from {lua_path}")
        with open(lua_path, 'r') as f:
            return f.read()
    else:
        logging.info("Using default Lua script")
        from main import SEARCH_SCRIPT
        return SEARCH_SCRIPT

def init_database() -> sqlite3.Connection:
    """Initialize SQLite database with required tables"""
    db_path = get_db_path()
    
    logging.info(f"Connecting to database at {db_path}")
    conn = sqlite3.connect(db_path)
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

def main():
    # Get the Lua script to use
    SEARCH_SCRIPT = get_lua_script()
    
    # Get configuration from environment variables with defaults
    START_DATE = get_env('START_DATE', '2020-01-01')
    END_DATE = get_env('END_DATE', datetime.now().strftime('%Y-%m-%d'))
    
    # Initialize database
    conn = init_database()
    
    # Check if Splash is ready - simple connectivity test
    splash_url = get_env('SPLASH_URL', 'http://splash:8050')
    logging.info(f"Testing connection to Splash at {splash_url}")
    
    # Wait for Splash service to be ready
    max_retries = 10
    retry_count = 0
    while retry_count < max_retries:
        try:
            import requests
            response = requests.get(f"{splash_url}/_ping", timeout=5)
            if response.status_code == 200:
                logging.info("Successfully connected to Splash service")
                break
        except Exception as e:
            logging.info(f"Waiting for Splash service to be ready... ({retry_count+1}/{max_retries})")
            time.sleep(5)
        retry_count += 1
    
    if retry_count >= max_retries:
        logging.error("Could not connect to Splash service after multiple attempts")
        return
    
    try:
        # Get daily dates
        dates = generate_date_range(START_DATE, END_DATE)
        total_days = len(dates)
        
        logging.info(f"Starting collection for {total_days} days from {START_DATE} to {END_DATE}")
        
        # Import crawler process here to avoid circular imports
        from scrapy.crawler import CrawlerProcess
        from urllib.parse import quote
        from scrapy_splash import SplashRequest
        
        # Process each day
        for idx, date in enumerate(dates, 1):
            logging.info(f"\nProcessing date: {date} ({idx}/{total_days})")
            
            # Configure crawler with environment variables
            process = CrawlerProcess({
                'LOG_LEVEL': get_env('LOG_LEVEL', 'INFO'),
                'COOKIES_ENABLED': True,
                'RETRY_TIMES': get_env_int('RETRY_TIMES', '3'),
                'DOWNLOAD_TIMEOUT': get_env_int('DOWNLOAD_TIMEOUT', '90'),
            })
            
            # Create a Docker-compatible spider
            class DockerGoogleSearchSpider(GoogleSearchSpider):
                custom_settings = GoogleSearchSpider.custom_settings.copy()
                # Override Splash URL with Docker service name
                custom_settings['SPLASH_URL'] = splash_url
                
                def __init__(self, date: str = None, *args, **kwargs):
                    super(GoogleSearchSpider, self).__init__(*args, **kwargs)
                    self.date = date
                    self.conn = init_database()
                    self.results_count = 0
                    self.max_results = get_env_int('MAX_RESULTS', '20')
                    
                def start_requests(self):
                    base_url = "https://www.google.com/search"
                    query = f'site:bloomberg.com intitle:nuclear "{self.date}"'
                    url = f"{base_url}?q={quote(query)}&num=20"
                    
                    logging.info(f"Starting request to {url}")
                    
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
            
            # Start crawling with the Docker-compatible spider
            process.crawl(DockerGoogleSearchSpider, date=date)
            process.start()
            
            # Force a reset of the crawler process
            process.stop()
            
            # Add random delay between days
            delay = random.uniform(
                get_env_float('MIN_DELAY', '120'), 
                get_env_float('MAX_DELAY', '180')
            )
            logging.info(f"Waiting {delay:.1f} seconds before next day...")
            time.sleep(delay)
            
    except Exception as e:
        logging.error(f"Error during execution: {str(e)}")
        logging.error(traceback.format_exc())
    finally:
        conn.close()

if __name__ == "__main__":
    main()
