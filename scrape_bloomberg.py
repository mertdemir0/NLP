"""Script to run the Bloomberg scraper."""
from src.data_ingestion.bloomberg_scraper import BloombergScraper
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run the Bloomberg scraper."""
    try:
        # Initialize and run scraper
        scraper = BloombergScraper()
        scraper.run()
        
    except Exception as e:
        logger.error(f"Error running Bloomberg scraper: {str(e)}")

if __name__ == "__main__":
    main()
