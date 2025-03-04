#!/usr/bin/env python3
"""Script to scrape Bloomberg articles about nuclear from 2020-2025."""
import argparse
import logging
import os
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
from tqdm import tqdm

from src.data_ingestion.historical_news_scraper import HistoricalNewsScraper
from src.database.bloomberg_db import BloombergDB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bloomberg_nuclear_scraping.log')
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Bloomberg Nuclear Articles Scraper')
    
    parser.add_argument('--start-date', type=str, default='2020-01-01',
                        help='Start date in YYYY-MM-DD format (default: 2020-01-01)')
    
    parser.add_argument('--end-date', type=str, default='2025-03-31',
                        help='End date in YYYY-MM-DD format (default: 2025-03-31)')
    
    parser.add_argument('--query', type=str, default='nuclear',
                        help='Search query (default: nuclear)')
    
    parser.add_argument('--headless', action='store_true', default=True,
                        help='Run browser in headless mode (default: True)')
    
    parser.add_argument('--workers', type=int, default=1,
                        help='Number of parallel workers (default: 1)')
    
    parser.add_argument('--chunk-months', type=int, default=3,
                        help='Number of months to scrape in each chunk (default: 3)')
    
    parser.add_argument('--db-path', type=str, default='data/bloomberg_nuclear.db',
                        help='Path to SQLite database (default: data/bloomberg_nuclear.db)')
    
    parser.add_argument('--resume', action='store_true',
                        help='Resume from last scraped date (default: False)')
    
    return parser.parse_args()

def get_date_chunks(start_date_str, end_date_str, chunk_months):
    """Split the date range into chunks of specified months.
    
    Args:
        start_date_str: Start date in YYYY-MM-DD format
        end_date_str: End date in YYYY-MM-DD format
        chunk_months: Number of months in each chunk
        
    Returns:
        List of (chunk_start_date, chunk_end_date) tuples
    """
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    chunks = []
    chunk_start = start_date
    
    while chunk_start < end_date:
        # Calculate chunk end date (chunk_start + chunk_months)
        chunk_end = chunk_start + relativedelta(months=chunk_months) - timedelta(days=1)
        
        # If chunk end is beyond the overall end date, use the overall end date
        if chunk_end > end_date:
            chunk_end = end_date
        
        # Add the chunk to the list
        chunks.append((
            chunk_start.strftime('%Y-%m-%d'),
            chunk_end.strftime('%Y-%m-%d')
        ))
        
        # Move to the next chunk
        chunk_start = chunk_end + timedelta(days=1)
    
    return chunks

def main():
    """Run the Bloomberg nuclear articles scraper."""
    args = parse_args()
    
    logger.info(f"Starting Bloomberg nuclear articles scraper")
    logger.info(f"Date range: {args.start_date} to {args.end_date}")
    logger.info(f"Query: {args.query}")
    
    # Initialize database
    db = BloombergDB(db_path=args.db_path)
    
    # Initialize scraper
    scraper = HistoricalNewsScraper(
        headless=args.headless,
        max_workers=args.workers,
        data_dir='data/bloomberg_nuclear'
    )
    
    # Get date chunks
    date_chunks = get_date_chunks(args.start_date, args.end_date, args.chunk_months)
    logger.info(f"Split date range into {len(date_chunks)} chunks")
    
    # If resuming, get the last scraped date
    if args.resume:
        metadata = db.get_scraping_metadata(args.start_date, args.end_date, args.query)
        if metadata and metadata['last_scraped_date']:
            # Find the chunk that contains the last scraped date
            last_date = metadata['last_scraped_date']
            for i, (chunk_start, chunk_end) in enumerate(date_chunks):
                if chunk_start <= last_date <= chunk_end:
                    # Resume from the next chunk
                    date_chunks = date_chunks[i+1:]
                    logger.info(f"Resuming from {date_chunks[0][0]} (after {last_date})")
                    break
    
    # Initialize counters
    total_articles = 0
    total_new_articles = 0
    
    # Process each date chunk
    for i, (chunk_start, chunk_end) in enumerate(tqdm(date_chunks, desc="Processing date chunks")):
        logger.info(f"Processing chunk {i+1}/{len(date_chunks)}: {chunk_start} to {chunk_end}")
        
        try:
            # Search Bloomberg for articles in this date range
            articles = scraper._search_bloomberg(args.query, chunk_start, chunk_end)
            
            if articles:
                logger.info(f"Found {len(articles)} articles in date range {chunk_start} to {chunk_end}")
                total_articles += len(articles)
                
                # Fetch full content for each article
                articles_with_content = scraper.fetch_article_content(articles)
                
                # Insert articles into database
                new_articles = db.insert_articles(articles_with_content)
                total_new_articles += new_articles
                
                # Update scraping metadata
                db.update_scraping_metadata(
                    args.start_date,
                    args.end_date,
                    args.query,
                    chunk_end,
                    total_new_articles,
                    "in_progress"
                )
            else:
                logger.info(f"No articles found in date range {chunk_start} to {chunk_end}")
            
            # Add a delay between chunks to avoid rate limiting
            time.sleep(5)
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_start} to {chunk_end}: {str(e)}", exc_info=True)
            # Update metadata with error status
            db.update_scraping_metadata(
                args.start_date,
                args.end_date,
                args.query,
                chunk_end,
                total_new_articles,
                f"error: {str(e)}"
            )
    
    # Update metadata with completed status
    db.update_scraping_metadata(
        args.start_date,
        args.end_date,
        args.query,
        args.end_date,
        total_new_articles,
        "completed"
    )
    
    # Print summary
    logger.info(f"Scraping complete!")
    logger.info(f"Total articles found: {total_articles}")
    logger.info(f"New articles added to database: {total_new_articles}")
    logger.info(f"Total articles in database: {db.get_article_count()}")
    
    # Export to JSON
    export_path = f"data/bloomberg_nuclear/bloomberg_nuclear_{datetime.now().strftime('%Y%m%d')}.json"
    db.export_to_json(export_path)
    logger.info(f"Exported all articles to {export_path}")
    
    # Close database connection
    db.close()

if __name__ == "__main__":
    main() 