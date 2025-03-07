"""Script to run the nuclear news scraper."""
from src.data_ingestion.news_scraper import NewsScraper
from src.database.models import ArticleDB
import json
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraping.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Run the news scraper."""
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Initialize database
    db = ArticleDB()
    
    # Initialize scraper with parallel processing settings
    scraper = NewsScraper(
        max_workers=3,    # Reduced workers for testing
        chunk_size=2      # Smaller chunks for testing
    )
    
    # Scrape articles from all sources
    logger.info("Starting article scraping...")
    
    # Run scraper for all pages (0-691)
    # Process in chunks of 10 pages to avoid overwhelming the server
    start_page = 0
    end_page = 691  # Total number of pages on IAEA news
    chunk_size = 10
    
    articles = []
    for chunk_start in range(start_page, end_page, chunk_size):
        chunk_end = min(chunk_start + chunk_size, end_page)
        logger.info(f"Processing pages {chunk_start} to {chunk_end}")
        articles.extend(scraper.scrape_all_sources(chunk_start, chunk_end))
    
    # Save to database
    new_articles = 0
    for article in articles:
        if db.insert_article(article):
            new_articles += 1
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'data/nuclear_articles_{timestamp}.json'
    
    # Save articles to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    
    # Log results
    logger.info(f"Scraping complete! Found {len(articles)} articles")
    logger.info(f"Added {new_articles} new articles to database")
    logger.info(f"JSON backup saved to: {output_file}")
    
    # Print database statistics
    total_articles = db.get_article_count()
    source_stats = db.get_source_statistics()
    
    logger.info("\nDatabase Statistics:")
    logger.info(f"Total articles in database: {total_articles}")
    logger.info("\nArticles by source:")
    for source, count in source_stats.items():
        logger.info(f"- {source}: {count} articles")
    
    # Print sample of articles
    if articles:
        logger.info("\nSample of collected articles:")
        for article in articles[:3]:
            logger.info(f"\nTitle: {article['title']}")
            logger.info(f"Source: {article['source']}")
            logger.info(f"Date: {article['date']}")
            logger.info(f"URL: {article['url']}")
            logger.info(f"Content preview: {article['content'][:200]}...")
            logger.info("-" * 80)

if __name__ == "__main__":
    main()
