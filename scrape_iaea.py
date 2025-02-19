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
        # Initialize scraper
        scraper = IAEAScraper()
        
        # Scrape first page only
        logger.info("Scraping first page of IAEA news articles...")
        articles = scraper.scrape_page(0)
        
        # Save articles
        if articles:
            logger.info(f"Found {len(articles)} articles, saving to database...")
            scraper.save_articles(articles)
        
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")

if __name__ == "__main__":
    main()
