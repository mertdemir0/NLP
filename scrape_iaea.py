"""Script to run the IAEA news scraper."""
import os
from src.data_ingestion.iaea_scraper import IAEAScraper
import logging

# Configure logging to see detailed progress
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

def main():
    """Run the IAEA scraper."""
    # Initialize scraper with conservative settings
    scraper = IAEAScraper(
        max_workers=3,  # Number of parallel workers
        chunk_size=3    # Pages per chunk
    )
    
    # Test with first 3 pages
    articles = scraper.scrape_articles(start_page=0, end_page=2)  # 0, 1, 2 = 3 pages
    
    logging.info(f"Scraping complete! Found {len(articles)} articles")

if __name__ == "__main__":
    main()
