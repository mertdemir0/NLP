"""Script to run the content scraper."""
from src.data_ingestion.content_scraper import ContentScraper
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run the content scraper."""
    try:
        # Initialize content scraper
        scraper = ContentScraper(chunk_size=10)
        
        # Start scraping content
        logger.info("Starting content scraping for nuclear-related articles...")
        scraper.run()
        
        logger.info("Content scraping complete!")
        
    except Exception as e:
        logger.error(f"Error running content scraper: {str(e)}")

if __name__ == "__main__":
    main()
