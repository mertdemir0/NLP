"""Script to run the IAEA scraper."""
import os
from src.data_ingestion.iaea_scraper import IAEAScraper
import logging

# Configure logging to see detailed progress
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

def main():
    """Run the IAEA scraper."""
    try:
        # Initialize scraper with 4 worker processes
        scraper = IAEAScraper(
            max_workers=4,  # Number of parallel workers
        )
        
        # Test with first 3 pages
        articles = scraper.scrape_articles(start_page=0, end_page=2)  # 0, 1, 2 = 3 pages
        
        logger.info(f"Scraping complete! Found {len(articles)} articles")
        
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")

if __name__ == "__main__":
    main()
