"""Script to scrape content from Bloomberg articles."""
from src.data_ingestion.bloomberg_content_scraper import BloombergContentScraper
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run the Bloomberg content scraper."""
    try:
        scraper = BloombergContentScraper()
        scraper.run()
        
    except Exception as e:
        logger.error(f"Error running Bloomberg content scraper: {str(e)}")

if __name__ == "__main__":
    main()
