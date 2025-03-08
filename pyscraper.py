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
from typing import Optional, Tuple
from urllib.parse import urlparse

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
    
    # Keep existing tables for Google News data
    c.execute('''CREATE TABLE IF NOT EXISTS raw_articles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  google_link TEXT UNIQUE,
                  published TEXT,
                  published_parsed DATE,
                  summary TEXT,
                  html_summary TEXT,
                  fetch_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS clean_articles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  google_link TEXT UNIQUE,
                  published TEXT,
                  published_parsed DATE,
                  summary TEXT,
                  raw_id INTEGER,
                  processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(raw_id) REFERENCES raw_articles(id))''')
    
    # New table for Google Search results
    c.execute('''CREATE TABLE IF NOT EXISTS google_search_articles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  url TEXT UNIQUE,
                  title TEXT,
                  fetch_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create indices for better performance
    c.execute('CREATE INDEX IF NOT EXISTS idx_google_link ON raw_articles(google_link)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_published_parsed ON clean_articles(published_parsed)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_search_url ON google_search_articles(url)')
    
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
        query = f'site:bloomberg.com intitle:nuclear'
        logging.info(f"Searching for: {query}")
        
        cursor = conn.cursor()
        total_processed = 0
        total_added = 0
        
        # Use Google Search
        search_results = search(query, num_results=100, lang="en")
        
        for url in search_results:
            try:
                if not is_valid_bloomberg_url(url):
                    continue
                
                # Store in google_search_articles table
                cursor.execute('''
                    INSERT OR IGNORE INTO google_search_articles 
                    (url)
                    VALUES (?)
                ''', (url,))
                
                if cursor.rowcount > 0:
                    total_added += 1
                    logging.info(f"Added: {url}")
                
                total_processed += 1
                
                # Add a small delay between requests to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"Error processing URL {url}: {str(e)}")
                continue
        
        conn.commit()
        logging.info(f"Successfully processed {total_processed} URLs, added {total_added} new articles")
        return total_processed, total_added
        
    except Exception as e:
        logging.error(f"Error fetching articles: {str(e)}")
        conn.rollback()
        return 0, 0

def generate_daily_ranges(start_date: str, end_date: str) -> list:
    """Generate a list of daily dates"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
    
    return dates

def get_progress_stats(conn: sqlite3.Connection) -> None:
    """Print detailed statistics about the collected articles"""
    cursor = conn.cursor()
    
    # Stats for Google News articles
    cursor.execute('SELECT COUNT(*) FROM raw_articles')
    raw_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM clean_articles')
    clean_count = cursor.fetchone()[0]
    
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
    logging.info("Google News Articles:")
    logging.info(f"  - Raw articles: {raw_count}")
    logging.info(f"  - Clean articles: {clean_count}")
    logging.info("\nGoogle Search Articles:")
    logging.info(f"  - Total articles: {search_count}")
    logging.info("\nDaily distribution (Google Search):")
    
    for date, count in daily_stats:
        logging.info(f"{date}: {count} articles")

if __name__ == "__main__":
    START_DATE = '2020-01-01'
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    DELAY_BETWEEN_DAYS = 2  # seconds
    
    # Initialize database
    conn = init_database()
    
    try:
        # Get daily dates
        dates = generate_daily_ranges(START_DATE, END_DATE)
        total_days = len(dates)
        
        logging.info(f"Starting collection for {total_days} days from {START_DATE} to {END_DATE}")
        
        # Process each day
        for idx, date in enumerate(dates, 1):
            logging.info(f"\nProcessing date: {date} ({idx}/{total_days})")
            
            processed, added = get_nuclear_articles_for_date(conn, date)
            
            # Add a delay between days
            time.sleep(DELAY_BETWEEN_DAYS)
        
        # Print final statistics
        get_progress_stats(conn)
            
    finally:
        conn.close()