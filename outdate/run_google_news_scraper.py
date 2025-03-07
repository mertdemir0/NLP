#!/usr/bin/env python3
"""Script to run the Google Search scraper."""
import argparse
import logging
from datetime import datetime
from src.data_ingestion.google_news_scraper import GoogleSearchScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('google_search_scraping.log')
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run Google Search scraper for news articles')
    
    parser.add_argument('--query', type=str, required=True,
                        help='Search query')
    
    parser.add_argument('--start-date', type=str, required=True,
                        help='Start date in YYYY-MM-DD format')
    
    parser.add_argument('--end-date', type=str, required=True,
                        help='End date in YYYY-MM-DD format')
    
    parser.add_argument('--no-headless', action='store_true',
                        help='Run browser in visible mode (default: run in headless mode)')
    
    parser.add_argument('--workers', type=int, default=3,
                        help='Number of parallel workers (default: 3)')
    
    parser.add_argument('--output-dir', type=str, default='data/google_search',
                        help='Directory to store scraped data (default: data/google_search)')
    
    return parser.parse_args()

def main():
    """Run the Google Search scraper."""
    args = parse_args()
    
    logger.info(f"Starting Google Search scraper with query: '{args.query}'")
    logger.info(f"Date range: {args.start_date} to {args.end_date}")
    
    try:
        # Initialize scraper
        scraper = GoogleSearchScraper(
            headless=not args.no_headless,  # Invert the no-headless flag
            use_proxy=False,
            max_workers=args.workers,
            data_dir=args.output_dir
        )
        
        # Run scraper
        articles = scraper.run(
            query=args.query,
            start_date=args.start_date,
            end_date=args.end_date
        )
        
        # Save results
        if articles:
            scraper.save_articles(articles)
            scraper.save_to_csv(articles)
        
        # Print summary
        logger.info(f"Scraping complete! Found {len(articles)} articles")
        
        # Print sample of articles
        if articles:
            logger.info("\nSample of collected articles:")
            for article in articles[:3]:
                logger.info(f"\nTitle: {article['title']}")
                logger.info(f"Source: {article['source']}")
                logger.info(f"Date: {article['date']}")
                logger.info(f"URL: {article['url']}")
                if 'snippet' in article:
                    logger.info(f"Snippet: {article['snippet']}")
                logger.info("-" * 80)
        
    except Exception as e:
        logger.error(f"Error running Google Search scraper: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
