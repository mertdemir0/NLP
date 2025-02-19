"""Script to run the IAEA scraper."""
from src.data_ingestion.iaea_scraper import IAEAScraper
import logging
import os

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
        # Initialize scraper with chunk size of 5
        scraper = IAEAScraper(chunk_size=5)
        
        # Scrape all pages (0-691)
        logger.info("Starting full scrape of IAEA news articles...")
        articles = scraper.scrape_articles(start_page=0, end_page=691)
        
        logger.info(f"Scraping complete! Found {len(articles)} unique articles")
        
        # Save articles
        if articles:
            logger.info(f"Found {len(articles)} articles, saving to database...")
            scraper.save_articles(articles)
        
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")

if __name__ == "__main__":
    main()
