#!/usr/bin/env python
"""
Direct scraper using Selenium to bypass Google's anti-scraping measures
"""
import os
import sys
import time
import random
import logging
import json
import sqlite3
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Add project directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from docker_config import get_env, get_env_int, get_db_path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import generate_date_range

def init_database():
    """Initialize and return a database connection"""
    db_path = get_db_path()
    logging.info(f"Connecting to database at {db_path}")
    conn = sqlite3.connect(db_path)
    
    # Create tables if not exists
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scrapy_articles (
        id INTEGER PRIMARY KEY,
        url TEXT UNIQUE,
        title TEXT,
        date TEXT,
        content TEXT,
        search_date TEXT,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    
    return conn

def fetch_bloomberg_articles_for_date(date, conn):
    """
    Fetch Bloomberg articles for a specific date using Selenium
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    
    # Initialize Chrome options
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # User agent rotation
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0'
    ]
    chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
    
    # Get configuration
    max_results = get_env_int('MAX_RESULTS', 20)
    
    # Prepare search query
    query = f'site:bloomberg.com intitle:nuclear "{date}"'
    search_url = f"https://www.google.com/search?q={query}&num={max_results}"
    
    driver = None
    articles_found = 0
    
    try:
        # Initialize driver
        logging.info(f"Starting Chrome WebDriver for date: {date}")
        driver = webdriver.Chrome(options=chrome_options)
        
        # Set page load timeout
        driver.set_page_load_timeout(30)
        
        # Navigate to Google
        logging.info(f"Navigating to: {search_url}")
        driver.get(search_url)
        
        # Wait for results to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "search"))
        )
        
        # Wait a bit and scroll down to load all content
        time.sleep(2)
        driver.execute_script("window.scrollBy(0, 500)")
        time.sleep(1)
        driver.execute_script("window.scrollBy(0, 500)")
        time.sleep(1)
        
        # Take screenshot for debugging
        debug_dir = os.path.join(os.environ.get('DATA_DIR', 'data'), 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        driver.save_screenshot(os.path.join(debug_dir, f"selenium_google_{date}.png"))
        
        # Check for captcha (for debugging)
        page_text = driver.page_source.lower()
        if "captcha" in page_text or "unusual traffic" in page_text:
            logging.warning(f"Captcha detected for date {date}!")
            with open(os.path.join(debug_dir, f"captcha_page_{date}.html"), 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
        
        # Find all result links to Bloomberg
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='bloomberg.com']")
        bloomberg_links = []
        
        for link in links:
            try:
                href = link.get_attribute('href')
                if href and 'bloomberg.com' in href:
                    # Get the title element which is a child of the parent div
                    parent = link.find_element(By.XPATH, "./..")
                    title_element = parent.find_element(By.CSS_SELECTOR, "h3") if parent else None
                    title = title_element.text if title_element else "Unknown Title"
                    
                    bloomberg_links.append({
                        'url': href,
                        'title': title
                    })
            except Exception as e:
                logging.error(f"Error extracting link info: {str(e)}")
        
        # Log the number of links found
        logging.info(f"Found {len(bloomberg_links)} Bloomberg links for date {date}")
        
        # Save to database
        cursor = conn.cursor()
        for article in bloomberg_links:
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO scrapy_articles (url, title, date, content, search_date) VALUES (?, ?, ?, ?, ?)",
                    (article['url'], article['title'], date, "", date)
                )
                if cursor.rowcount > 0:
                    articles_found += 1
            except Exception as e:
                logging.error(f"Error saving article to database: {str(e)}")
        
        conn.commit()
        logging.info(f"Saved {articles_found} new articles to database for date {date}")
        
        return articles_found
        
    except TimeoutException:
        logging.error(f"Timeout loading Google search results for date {date}")
        return 0
    except WebDriverException as e:
        logging.error(f"WebDriver error for date {date}: {str(e)}")
        return 0
    except Exception as e:
        logging.error(f"Unexpected error for date {date}: {str(e)}")
        return 0
    finally:
        if driver:
            driver.quit()

def main():
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
        
        # Process each day
        success_count = 0
        total_articles = 0
        
        for idx, date in enumerate(dates, 1):
            logging.info(f"\nProcessing date: {date} ({idx}/{total_days})")
            
            # Fetch articles for this date
            articles_found = fetch_bloomberg_articles_for_date(date, conn)
            total_articles += articles_found
            
            if articles_found > 0:
                success_count += 1
            
            # Add random delay between days (shorter to speed up debugging)
            if idx < total_days:  # No need to delay after the last date
                delay = random.uniform(
                    get_env_int('MIN_DELAY', 5),
                    get_env_int('MAX_DELAY', 15)
                )
                logging.info(f"Waiting {delay:.1f} seconds before next day...")
                time.sleep(delay)
        
        logging.info(f"Processing completed. Successfully found articles for {success_count}/{total_days} days.")
        logging.info(f"Total articles found: {total_articles}")
            
    except Exception as e:
        logging.error(f"Error during execution: {str(e)}")
        logging.error(traceback.format_exc())
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
