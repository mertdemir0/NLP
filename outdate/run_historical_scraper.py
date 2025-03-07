#!/usr/bin/env python3
"""Script to run the historical news scraper."""
import argparse
import logging
from datetime import datetime, timedelta
from src.data_ingestion.historical_news_scraper import HistoricalNewsScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('historical_scraping.log')
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Historical News Scraper')
    
    parser.add_argument('--query', type=str, required=True,
                        help='Search query (e.g., "nuclear energy")')
    
    parser.add_argument('--start-date', type=str,
                        help='Start date in YYYY-MM-DD format (default: 30 days ago)')
    
    parser.add_argument('--end-date', type=str,
                        help='End date in YYYY-MM-DD format (default: today)')
    
    parser.add_argument('--headless', action='store_true', default=True,
                        help='Run browser in headless mode (default: True)')
    
    parser.add_argument('--no-content', action='store_true',
                        help='Skip fetching article content (default: False)')
    
    parser.add_argument('--workers', type=int, default=3,
                        help='Number of parallel workers (default: 3)')
    
    parser.add_argument('--output-dir', type=str, default='data/historical_news',
                        help='Directory to store scraped data (default: data/historical_news)')
    
    return parser.parse_args()

def main():
    """Run the historical news scraper."""
    args = parse_args()
    
    # Set default dates if not provided
    if not args.start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    else:
        start_date = args.start_date
    
    if not args.end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    else:
        end_date = args.end_date
    
    logger.info(f"Starting historical news scraper with query: '{args.query}'")
    logger.info(f"Date range: {start_date} to {end_date}")
    
    try:
        # Initialize scraper
        scraper = HistoricalNewsScraper(
            headless=args.headless,
            max_workers=args.workers,
            data_dir=args.output_dir
        )
        
        # Run scraper
        articles = scraper.run(
            query=args.query,
            start_date=start_date,
            end_date=end_date,
            fetch_content=not args.no_content
        )
        
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
                if 'text' in article:
                    logger.info(f"Content preview: {article['text'][:200]}...")
                logger.info("-" * 80)
        
    except Exception as e:
        logger.error(f"Error running historical news scraper: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main() 