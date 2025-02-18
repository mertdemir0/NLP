"""Test script for the news scraper."""
import logging
from src.data_ingestion.news_scraper import NewsScraper
from src.database.models import ArticleDB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # Initialize scraper with basic config
    config = {
        'max_retries': 3,
        'request_timeout': 30,
        'user_agent_rotation': True
    }
    
    scraper = NewsScraper(config)
    
    # Run scraper for nuclear energy news
    articles = scraper.run(
        query="nuclear energy safety regulations",
        days=30,
        output_dir="data/raw"
    )
    
    # Print results
    db = ArticleDB()
    all_articles = db.get_all_articles()
    print(f"\nTotal articles in database: {len(all_articles)}")
    
    if all_articles:
        print("\nMost recent articles:")
        for article in all_articles[:5]:
            print(f"\nTitle: {article['title']}")
            print(f"Source: {article['source']}")
            print(f"Date: {article['published_date']}")
            print(f"URL: {article['url']}")
            print("-" * 80)

if __name__ == "__main__":
    main()
