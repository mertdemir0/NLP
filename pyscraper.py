from googlesearch import search
import json
from datetime import datetime, timedelta
import pandas as pd
import os
import time
import sqlite3
import re
from bs4 import BeautifulSoup
import logging
from typing import Optional, Tuple, List
from urllib.parse import urlparse
import concurrent.futures
import requests
from fake_useragent import UserAgent
from itertools import cycle

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

def init_database() -> sqlite3.Connection:
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('nuclear_news.db')
    c = conn.cursor()
    
    # Only keep Google Search table
    c.execute('''CREATE TABLE IF NOT EXISTS google_search_articles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  url TEXT,
                  title TEXT,
                  fetch_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    return conn

def is_valid_bloomberg_url(url: str) -> bool:
    """Check if URL is a valid Bloomberg article URL"""
    try:
        parsed = urlparse(url)
        return (parsed.netloc.endswith('bloomberg.com') and 
                not any(x in url.lower() for x in ['/videos/', '/audio/', '/podcasts/']))
    except:
        return False

def get_free_proxies() -> List[str]:
    """Get a list of free proxies from various sources"""
    proxies = set()
    
    # Free proxy list
    url = "https://free-proxy-list.net/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    for row in soup.find("table", attrs={"class": "table table-striped table-bordered"}).find_all("tr")[1:]:
        tds = row.find_all("td")
        try:
            ip = tds[0].text.strip()
            port = tds[1].text.strip()
            https = tds[6].text.strip()
            if https == "yes":
                proxies.add(f"http://{ip}:{port}")
        except:
            continue
    
    return list(proxies)

def search_with_proxy(query: str, proxy: str, page: int = 0, num_results: int = 100) -> List[str]:
    """Perform Google search using a proxy"""
    try:
        # Modify query to include page information using time ranges
        if page > 0:
            # Add time range to help with pagination
            query = f"{query} when:{page*10}-{(page+1)*10}"
        
        # Add sleep to avoid rate limiting
        time.sleep(2.0)
        
        results = list(search(
            query,
            num_results=num_results,
            lang="en",
            proxy=proxy
        ))
        return results
    except Exception as e:
        logging.error(f"Error with proxy {proxy}: {str(e)}")
        return []

def get_nuclear_articles_for_date(conn: sqlite3.Connection, date: str) -> Tuple[int, int]:
    """
    Fetch nuclear-related articles from Bloomberg for a specific date using parallel processing and multiple pages
    Args:
        conn: SQLite connection
        date: Date in YYYY-MM-DD format
    Returns:
        Tuple of (total_processed, total_added) counts
    """
    try:
        base_query = f'site:bloomberg.com intitle:nuclear "{date}"'
        logging.info(f"Searching for: {base_query}")
        
        cursor = conn.cursor()
        total_processed = 0
        total_added = 0
        
        # Get free proxies
        proxies = get_free_proxies()
        if not proxies:
            logging.warning("No proxies available, using direct connection")
            proxies = [None]
        
        proxy_pool = cycle(proxies)
        
        # Create search tasks for different time ranges to simulate pagination
        tasks = []
        max_pages = 5  # Further reduced number of pages to avoid rate limiting
        for page in range(max_pages):
            proxy = next(proxy_pool)
            tasks.append((base_query, proxy, page, 50))  # Reduced results per page
        
        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:  # Reduced workers
            future_to_search = {
                executor.submit(search_with_proxy, q, p, pg, n): (q, p, pg, n) 
                for q, p, pg, n in tasks
            }
            
            empty_result_count = 0  # Track consecutive empty results
            
            for future in concurrent.futures.as_completed(future_to_search):
                try:
                    urls = future.result()
                    
                    if not urls:
                        empty_result_count += 1
                        if empty_result_count >= 2:  # If 2 consecutive empty results, assume no more pages
                            logging.info("No more results found for this date")
                            break
                    else:
                        empty_result_count = 0  # Reset counter when we find results
                    
                    for url in urls:
                        try:
                            if not is_valid_bloomberg_url(url):
                                continue
                            
                            cursor.execute('''
                                INSERT INTO google_search_articles 
                                (url, fetch_date)
                                VALUES (?, ?)
                            ''', (url, date))
                            
                            total_added += 1
                            logging.info(f"Added: {url}")
                            total_processed += 1
                            
                        except Exception as e:
                            logging.error(f"Error processing URL {url}: {str(e)}")
                            continue
                            
                except Exception as e:
                    logging.error(f"Error in search thread: {str(e)}")
        
        conn.commit()
        logging.info(f"Successfully processed {total_processed} URLs, added {total_added} new articles for date {date}")
        return total_processed, total_added
        
    except Exception as e:
        logging.error(f"Error fetching articles: {str(e)}")
        conn.rollback()
        return 0, 0

def generate_daily_ranges(start_date: str, end_date: str) -> List[str]:
    """Generate a list of daily dates from start_date to end_date"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    dates = []
    
    while start <= end:
        dates.append(start.strftime('%Y-%m-%d'))
        start += timedelta(days=1)
    
    return dates

def get_progress_stats(conn: sqlite3.Connection) -> None:
    """Print detailed statistics about the collected articles"""
    cursor = conn.cursor()
    
    # Stats for Google Search articles
    cursor.execute('SELECT COUNT(*) FROM google_search_articles')
    search_count = cursor.fetchone()[0]
    
    # Get daily distribution for Google Search articles
    cursor.execute('''
        SELECT 
            DATE(fetch_date) as date,
            COUNT(*) as count
        FROM google_search_articles
        GROUP BY DATE(fetch_date)
        ORDER BY date
    ''')
    daily_stats = cursor.fetchall()
    
    # Print statistics
    logging.info("\nCollection Summary:")
    logging.info("Google Search Articles:")
    logging.info(f"  - Total articles: {search_count}")
    logging.info("\nDaily distribution (Google Search):")
    
    for date, count in daily_stats:
        logging.info(f"{date}: {count} articles")

if __name__ == "__main__":
    START_DATE = '2020-01-01'
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    DELAY_BETWEEN_DAYS = 5  # seconds, increased to avoid rate limiting
    
    # Initialize database
    conn = init_database()
    
    try:
        # Get daily dates
        dates = generate_daily_ranges(START_DATE, END_DATE)
        total_days = len(dates)
        
        logging.info(f"Starting collection for {total_days} days from {START_DATE} to {END_DATE}")
        
        total_processed = 0
        total_added = 0
        
        # Process each day
        for idx, date in enumerate(dates, 1):
            logging.info(f"\nProcessing date: {date} ({idx}/{total_days})")
            
            processed, added = get_nuclear_articles_for_date(conn, date)
            total_processed += processed
            total_added += added
            
            logging.info(f"Progress - Total processed: {total_processed}, Total added: {total_added}")
            
            # Add a delay between days
            time.sleep(DELAY_BETWEEN_DAYS)
        
        # Print final statistics
        get_progress_stats(conn)
        
    except Exception as e:
        logging.error(f"Error during execution: {str(e)}")
    finally:
        conn.close()