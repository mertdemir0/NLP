"""Script to run the IAEA scraper."""
from src.data_ingestion.iaea_scraper import IAEAScraper
import logging

# Configure logging
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
        # Initialize scraper with 10 concurrent tasks
        scraper = IAEAScraper(max_concurrent=10)
        
        # Start with 3 pages for testing
        articles = scraper.scrape_articles(start_page=0, end_page=2)
        
        logger.info(f"Scraping complete! Found {len(articles)} articles")
        
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")

if __name__ == "__main__":
    main()
