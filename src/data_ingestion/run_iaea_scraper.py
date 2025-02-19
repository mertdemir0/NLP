"""Script to run the IAEA scraper."""
from iaea_scraper import IAEAScraper
import logging

def main():
    """Run the IAEA scraper."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize scraper
        scraper = IAEAScraper(max_workers=3, chunk_size=5)
        
        # Run scraper (you can adjust the page range as needed)
        articles = scraper.scrape_articles(start_page=0, end_page=691)
        
        logger.info(f"Scraping completed. Total articles scraped: {len(articles)}")
        
    except Exception as e:
        logger.error(f"Error running scraper: {str(e)}")
        raise

if __name__ == "__main__":
    main()
