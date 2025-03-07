from pygooglenews import GoogleNews
import json
from datetime import datetime, timedelta
import pandas as pd
import os
import time
import sqlite3
import re
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse, parse_qs
import logging
from typing import Optional, Tuple

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
    
    # Raw table to store all fetched articles
    c.execute('''CREATE TABLE IF NOT EXISTS raw_articles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  google_link TEXT,
                  bloomberg_link TEXT,
                  published TEXT,
                  published_parsed DATE,
                  summary TEXT,
                  html_summary TEXT,
                  fetch_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Clean table with unique Bloomberg links
    c.execute('''CREATE TABLE IF NOT EXISTS clean_articles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  bloomberg_link TEXT UNIQUE,
                  published TEXT,
                  published_parsed DATE,
                  summary TEXT,
                  raw_id INTEGER,
                  processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(raw_id) REFERENCES raw_articles(id))''')
    
    # Create indices for better performance
    c.execute('CREATE INDEX IF NOT EXISTS idx_bloomberg_link ON raw_articles(bloomberg_link)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_published_parsed ON clean_articles(published_parsed)')
    
    conn.commit()
    return conn

def clean_html_summary(html_text: Optional[str]) -> Optional[str]:
    """Remove HTML formatting from summary"""
    if not html_text:
        return None
    # Remove HTML tags
    soup = BeautifulSoup(html_text, 'html.parser')
    text = soup.get_text(separator=' ').strip()
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove common artifacts
    text = text.replace('&nbsp;', ' ').strip()
    return text

def extract_bloomberg_url(google_link: str) -> Optional[str]:
    """Extract original Bloomberg URL from Google News link"""
    try:
        # For RSS feed links, we need to decode them first
        if 'news.google.com/rss/articles/' in google_link:
            response = requests.get(google_link, allow_redirects=True)
            if response.status_code == 200:
                google_link = response.url

        # Now parse the Google News URL
        parsed = urlparse(google_link)
        query_params = parse_qs(parsed.query)
        
        # Try to get the URL from different possible parameters
        url = None
        for param in ['url', 'u']:  # Some links use 'u' instead of 'url'
            if param in query_params:
                url = query_params[param][0]
                break
        
        if url and 'bloomberg.com' in url.lower():
            # Clean up the URL
            url = url.split('#')[0]  # Remove fragment
            url = url.split('?')[0]  # Remove query parameters
            return url
            
        return None
    except Exception as e:
        logging.error(f"Error extracting Bloomberg URL: {str(e)}")
        return None

def get_nuclear_news_by_date_range(conn: sqlite3.Connection, start_date: str, end_date: str, source: str = 'bloomberg.com') -> Tuple[int, int]:
    """
    Fetch nuclear-related news articles from a specific source within a date range
    Args:
        conn: SQLite connection
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        source: News source domain
    Returns:
        Tuple of (total_processed, total_added) counts
    """
    try:
        gn = GoogleNews(lang='en')
        logging.info(f"Searching for nuclear news from {source} between {start_date} and {end_date}")
        
        # Construct query with source restriction and intitle:nuclear
        query = f"intitle:nuclear site:{source}"
        
        # Search with date range
        search_results = gn.search(query, from_=start_date, to_=end_date)
        
        # Extract relevant information
        entries = search_results.get('entries', [])
        logging.info(f"Found {len(entries)} entries")
        
        cursor = conn.cursor()
        total_processed = 0
        total_added = 0
        
        for entry in entries:
            try:
                # Parse the publication date
                pub_date = datetime(*entry.published_parsed[:6])
                
                # Get Bloomberg URL
                bloomberg_url = extract_bloomberg_url(entry.link)
                if not bloomberg_url:
                    logging.warning(f"Could not extract Bloomberg URL from: {entry.link}")
                    continue
                
                logging.info(f"Processing article: {entry.title}")
                logging.info(f"Bloomberg URL: {bloomberg_url}")
                
                # Clean the summary
                html_summary = entry.summary if hasattr(entry, 'summary') else None
                clean_summary = clean_html_summary(html_summary)
                
                # Store in raw_articles table
                cursor.execute('''
                    INSERT INTO raw_articles 
                    (title, google_link, bloomberg_link, published, published_parsed, 
                     summary, html_summary)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entry.title,
                    entry.link,
                    bloomberg_url,
                    entry.published,
                    pub_date.strftime('%Y-%m-%d'),
                    clean_summary,
                    html_summary
                ))
                total_added += 1
                logging.info(f"Added article to database: {entry.title}")
                
            except (AttributeError, TypeError) as e:
                logging.error(f"Error processing entry: {str(e)}")
                continue
                
            total_processed += 1
        
        conn.commit()
        return total_processed, total_added
        
    except Exception as e:
        logging.error(f"Error fetching news: {str(e)}")
        conn.rollback()
        return 0, 0

def generate_daily_ranges(start_date: str, end_date: str) -> list:
    """Generate a list of daily date ranges"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    ranges = []
    current = start
    while current <= end:
        ranges.append((current.strftime('%Y-%m-%d'), current.strftime('%Y-%m-%d')))
        current += timedelta(days=1)
    
    return ranges

def update_clean_articles(conn: sqlite3.Connection) -> int:
    """
    Update clean_articles table with unique Bloomberg links
    Returns:
        Number of new articles added to clean table
    """
    cursor = conn.cursor()
    
    # Get current count
    cursor.execute('SELECT COUNT(*) FROM clean_articles')
    before_count = cursor.fetchone()[0]
    
    # Insert new articles with unique Bloomberg links
    cursor.execute('''
        INSERT OR IGNORE INTO clean_articles 
        (title, bloomberg_link, published, published_parsed, summary, raw_id)
        SELECT title, bloomberg_link, published, published_parsed, summary, id
        FROM raw_articles 
        WHERE bloomberg_link IS NOT NULL
        AND bloomberg_link NOT IN (SELECT bloomberg_link FROM clean_articles)
    ''')
    
    # Get new count
    cursor.execute('SELECT COUNT(*) FROM clean_articles')
    after_count = cursor.fetchone()[0]
    
    conn.commit()
    return after_count - before_count

def get_progress_stats(conn: sqlite3.Connection) -> None:
    """Print detailed statistics about the collected articles"""
    cursor = conn.cursor()
    
    # Count raw articles
    cursor.execute('SELECT COUNT(*) FROM raw_articles')
    raw_count = cursor.fetchone()[0]
    
    # Count unique articles
    cursor.execute('SELECT COUNT(*) FROM clean_articles')
    clean_count = cursor.fetchone()[0]
    
    # Get yearly distribution
    cursor.execute('''
        SELECT 
            strftime('%Y', published_parsed) as year,
            COUNT(*) as count,
            COUNT(DISTINCT strftime('%m', published_parsed)) as months_covered
        FROM clean_articles
        GROUP BY year
        ORDER BY year
    ''')
    yearly_stats = cursor.fetchall()
    
    # Print statistics
    logging.info("\nCollection Summary:")
    logging.info(f"Total raw articles: {raw_count}")
    logging.info(f"Unique articles: {clean_count}")
    logging.info("\nArticles per year (unique):")
    
    for year, count, months in yearly_stats:
        avg_per_month = count / months if months > 0 else 0
        logging.info(f"{year}: {count} articles across {months} months (avg: {avg_per_month:.1f}/month)")

if __name__ == "__main__":
    START_DATE = '2020-01-01'
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    SOURCE = 'bloomberg.com'
    DELAY_BETWEEN_REQUESTS = 5  # seconds
    MAX_RETRIES = 3
    
    # Initialize database
    conn = init_database()
    
    try:
        # Get daily ranges
        date_ranges = generate_daily_ranges(START_DATE, END_DATE)
        total_days = len(date_ranges)
        
        logging.info(f"Starting collection for {total_days} days from {START_DATE} to {END_DATE}")
        
        # Process each day
        for idx, (start, end) in enumerate(date_ranges, 1):
            logging.info(f"\nProcessing date: {start} ({idx}/{total_days})")
            
            # Try multiple times in case of rate limiting
            for attempt in range(MAX_RETRIES):
                try:
                    processed, added = get_nuclear_news_by_date_range(conn, start, end, SOURCE)
                    if processed > 0:
                        # Update clean articles table
                        new_unique = update_clean_articles(conn)
                        logging.info(f"Added {new_unique} new unique articles")
                        break
                except Exception as e:
                    if attempt < MAX_RETRIES - 1:
                        wait_time = DELAY_BETWEEN_REQUESTS * (attempt + 1)
                        logging.warning(f"Attempt {attempt + 1} failed. Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                    else:
                        logging.error(f"Failed to process {start} after {MAX_RETRIES} attempts")
            
            # Add a delay between successful requests
            time.sleep(DELAY_BETWEEN_REQUESTS)
        
        # Print final statistics
        get_progress_stats(conn)
            
    finally:
        conn.close()