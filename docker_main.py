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
import traceback
import time
import subprocess

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
from main import generate_date_range

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

def run_spider_for_date(date):
    """Run a separate process for each date to avoid reactor restart issues"""
    # Create a temporary Python script that runs just one spider for one date
    temp_script_path = '/tmp/run_spider_for_date.py'
    
    script_content = f"""#!/usr/bin/env python
import os
import sys
import logging
import random
from datetime import datetime

sys.path.append('{os.path.dirname(os.path.abspath(__file__))}')
from main import GoogleSearchSpider, USER_AGENTS
from docker_config import get_env, get_env_int, get_db_path, setup_signal_handlers
from urllib.parse import quote
from scrapy_splash import SplashRequest
from scrapy.crawler import CrawlerProcess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Get the Lua script
lua_path = '{get_env('LUA_SOURCE_PATH', None)}'
lua_script = ""
if lua_path and os.path.exists(lua_path):
    with open(lua_path, 'r') as f:
        lua_script = f.read()
else:
    from main import SEARCH_SCRIPT
    lua_script = SEARCH_SCRIPT

# Initialize database connection
def init_database():
    db_path = '{get_db_path()}'
    import sqlite3
    logging.info(f"Connecting to database at {{db_path}}")
    conn = sqlite3.connect(db_path)
    return conn

# Create custom spider for this date
class DockerGoogleSearchSpider(GoogleSearchSpider):
    custom_settings = GoogleSearchSpider.custom_settings.copy()
    # Override Splash URL with Docker service name
    custom_settings['SPLASH_URL'] = '{get_env('SPLASH_URL', 'http://splash:8050')}'
    
    def __init__(self, date: str = None, *args, **kwargs):
        super(GoogleSearchSpider, self).__init__(*args, **kwargs)
        self.date = date
        self.conn = init_database()
        self.results_count = 0
        self.max_results = {get_env_int('MAX_RESULTS', '20')}
        
    def start_requests(self):
        base_url = "https://www.google.com/search"
        query = f'site:bloomberg.com intitle:nuclear "{{self.date}}"'
        url = f"{{base_url}}?q={{quote(query)}}&num=20"
        
        logging.info(f"Starting request to {{url}}")
        
        yield SplashRequest(
            url,
            callback=self.parse_search_results,
            endpoint='execute',
            args={{
                'lua_source': lua_script,
                'user_agent': random.choice(USER_AGENTS),
                'wait': 5,
            }},
            meta={{'page': 1}}
        )

# Create and run the process
process = CrawlerProcess({{
    'LOG_LEVEL': '{get_env('LOG_LEVEL', 'INFO')}',
    'COOKIES_ENABLED': True,
    'RETRY_TIMES': {get_env_int('RETRY_TIMES', '3')},
    'DOWNLOAD_TIMEOUT': {get_env_int('DOWNLOAD_TIMEOUT', '90')},
}})

# Run the spider for just this date
process.crawl(DockerGoogleSearchSpider, date='{date}')
process.start()
"""

    # Write the temporary script
    with open(temp_script_path, 'w') as f:
        f.write(script_content)
    
    # Make it executable
    os.chmod(temp_script_path, 0o755)
    
    # Run the script as a separate process
    logging.info(f"Starting subprocess to process date: {date}")
    result = subprocess.run(
        ["python", temp_script_path],
        capture_output=True,
        text=True
    )
    
    # Log the results
    logging.info(f"Subprocess for date {date} completed with exit code: {result.returncode}")
    if result.stdout:
        logging.info(f"Subprocess stdout: {result.stdout}")
    if result.stderr:
        logging.error(f"Subprocess stderr: {result.stderr}")
    
    return result.returncode == 0

def main():
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
    
    # Get configuration from environment variables with defaults
    START_DATE = get_env('START_DATE', '2020-01-01')
    END_DATE = get_env('END_DATE', datetime.now().strftime('%Y-%m-%d'))
    
    # Initialize database
    conn = init_database()
    
    try:
        # Get daily dates
        dates = generate_date_range(START_DATE, END_DATE)
        total_days = len(dates)
        
        logging.info(f"Starting collection for {total_days} days from {START_DATE} to {END_DATE}")
        
        # Process each day in a separate process to avoid reactor issues
        success_count = 0
        for idx, date in enumerate(dates, 1):
            logging.info(f"\nProcessing date: {date} ({idx}/{total_days})")
            
            # Run spider in a separate process
            if run_spider_for_date(date):
                success_count += 1
            
            # Add random delay between days
            if idx < total_days:  # No need to delay after the last date
                delay = random.uniform(
                    get_env_float('MIN_DELAY', '15'), 
                    get_env_float('MAX_DELAY', '45')
                )
                logging.info(f"Waiting {delay:.1f} seconds before next day...")
                time.sleep(delay)
        
        logging.info(f"Processing completed. Successfully processed {success_count}/{total_days} days.")
            
    except Exception as e:
        logging.error(f"Error during execution: {str(e)}")
        logging.error(traceback.format_exc())
    finally:
        conn.close()

if __name__ == "__main__":
    main()
