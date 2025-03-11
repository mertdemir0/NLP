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
from itertools import cycle
import urllib3
import ssl

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    
    try:
        # Free proxy list
        url = "https://free-proxy-list.net/"
        response = requests.get(url, verify=False)  # Disable SSL verification
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
        
        if not proxies:
            logging.warning("No HTTPS proxies found, trying HTTP proxies")
            # If no HTTPS proxies, try HTTP ones
            for row in soup.find("table", attrs={"class": "table table-striped table-bordered"}).find_all("tr")[1:]:
                tds = row.find_all("td")
                try:
                    ip = tds[0].text.strip()
                    port = tds[1].text.strip()
                    proxies.add(f"http://{ip}:{port}")
                except:
                    continue
    except Exception as e:
        logging.error(f"Error fetching proxies: {str(e)}")
    
    return list(proxies)

def search_with_proxy(query: str, proxy: str, page: int = 0, num_results: int = 50) -> List[str]:
    """Perform Google search using a proxy"""
    try:
        # Modify query to include page information using time ranges
        if page > 0:
            # Add time range to help with pagination
            query = f"{query} when:{page*10}-{(page+1)*10}"
        
        # Add sleep to avoid rate limiting
        time.sleep(2.0)
        
        try:
            results = list(search(
                query,
                num_results=num_results,
                lang="en",
                proxy=proxy,
                verify_ssl=False  # Disable SSL verification
            ))
        except TypeError:
            # If verify_ssl is not supported, try without it
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
    Fetch nuclear-related articles from Bloomberg for a specific date
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
        
        # Try direct connection first
        try:
            logging.info("Trying direct connection first...")
            time.sleep(5.0)  # Add initial delay
            results = list(search(base_query, num_results=20, lang="en"))  # Reduced results per page
            
            for url in results:
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
            
            # If direct connection works, try one more page with longer delay
            if results:
                logging.info("Direct connection successful, trying one more page...")
                time.sleep(10.0)  # Longer delay between pages
                
                try:
                    query = f'{base_query} when:10-20'  # Add time range for second page
                    page_results = list(search(query, num_results=20, lang="en"))
                    
                    for url in page_results:
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
                    logging.error(f"Error fetching second page: {str(e)}")
            
            conn.commit()
            logging.info(f"Successfully processed {total_processed} URLs, added {total_added} new articles for date {date}")
            return total_processed, total_added
        
        except Exception as e:
            logging.warning(f"Direct connection failed: {str(e)}, trying with proxies...")
            time.sleep(30.0)  # Long delay before trying proxies
        
        # If direct connection fails, try with proxies
        proxies = get_free_proxies()
        if not proxies:
            logging.warning("No proxies available")
            return total_processed, total_added
        
        proxy_pool = cycle(proxies)
        proxy = next(proxy_pool)
        
        try:
            results = list(search(
                base_query,
                num_results=20,
                lang="en",
                proxy=proxy
            ))
            
            for url in results:
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
            logging.error(f"Error with proxy: {str(e)}")
        
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
    DELAY_BETWEEN_DAYS = 30  # seconds, increased significantly to avoid rate limiting
    
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
            
            # Add a longer delay between days
            time.sleep(DELAY_BETWEEN_DAYS)
        
        # Print final statistics
        get_progress_stats(conn)
        
    except Exception as e:
        logging.error(f"Error during execution: {str(e)}")
    finally:
        conn.close()