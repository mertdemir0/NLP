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

def search_with_proxy(query: str, proxy: str, start_index: int = 0, num_results: int = 100) -> List[str]:
    """Perform Google search using a proxy"""
    ua = UserAgent()
    headers = {'User-Agent': ua.random}
    
    try:
        results = list(search(
            query,
            start_index=start_index,
            num_results=num_results,
            lang="en",
            proxy=proxy,
            headers=headers
        ))
        return results
    except Exception as e:
        logging.error(f"Error with proxy {proxy}: {str(e)}")
        return []

def get_nuclear_articles(conn: sqlite3.Connection) -> Tuple[int, int]:
    """
    Fetch nuclear-related articles from Bloomberg using parallel processing and multiple pages
    """
    try:
        query = f'site:bloomberg.com intitle:nuclear'
        logging.info(f"Searching for: {query}")
        
        cursor = conn.cursor()
        total_processed = 0
        total_added = 0
        
        # Get free proxies
        proxies = get_free_proxies()
        if not proxies:
            logging.warning("No proxies available, using direct connection")
            proxies = [None]
        
        proxy_pool = cycle(proxies)
        
        # Create search tasks with different start indices to get multiple pages
        tasks = []
        for page in range(20):  # Try to get 20 pages
            start_index = page * 100
            proxy = next(proxy_pool)
            tasks.append((query, proxy, start_index, 100))
        
        # Use ThreadPoolExecutor for parallel processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_search = {
                executor.submit(search_with_proxy, q, p, s, n): (q, p, s, n) 
                for q, p, s, n in tasks
            }
            
            for future in concurrent.futures.as_completed(future_to_search):
                try:
                    urls = future.result()
                    
                    for url in urls:
                        try:
                            if not is_valid_bloomberg_url(url):
                                continue
                            
                            cursor.execute('''
                                INSERT INTO google_search_articles 
                                (url)
                                VALUES (?)
                            ''', (url,))
                            
                            total_added += 1
                            logging.info(f"Added: {url}")
                            total_processed += 1
                            
                        except Exception as e:
                            logging.error(f"Error processing URL {url}: {str(e)}")
                            continue
                            
                except Exception as e:
                    logging.error(f"Error in search thread: {str(e)}")
        
        conn.commit()
        logging.info(f"Successfully processed {total_processed} URLs, added {total_added} new articles")
        return total_processed, total_added
        
    except Exception as e:
        logging.error(f"Error fetching articles: {str(e)}")
        conn.rollback()
        return 0, 0

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
    # Initialize database
    conn = init_database()
    
    try:
        logging.info("Starting article collection")
        processed, added = get_nuclear_articles(conn)
        logging.info(f"\nCollection completed. Total processed: {processed}, Total added: {added}")
        
        # Print final statistics
        get_progress_stats(conn)
        
    except Exception as e:
        logging.error(f"Error during execution: {str(e)}")
    
    finally:
        conn.close()