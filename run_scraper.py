"""Script to run the news scraper with specific parameters."""
import logging
from src.data_ingestion.news_scraper import NewsScraper
from src.database.models import ArticleDB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    # Scraper configuration
    config = {
        'max_retries': 3,
        'request_timeout': 30,
        'user_agent_rotation': True,
        'search_sources': [
            'bloomberg.com',
            'reuters.com',
            'world-nuclear-news.org'
        ]
    }
    
    # Initialize scraper
    scraper = NewsScraper(config)
    
    # Define search parameters
    search_params = {
        'query': 'nuclear power plant safety regulations',  # Specific focus on safety
        'days': 30,  # Last 30 days
        'output_dir': 'data/raw'
    }
    
    try:
        # Run the scraper
        print(f"\nStarting scraper with parameters:")
        print(f"Query: {search_params['query']}")
        print(f"Time range: Last {search_params['days']} days")
        print(f"Output directory: {search_params['output_dir']}")
        print("\nScraping articles...")
        
        articles = scraper.run(**search_params)
        
        # Print results
        print(f"\nScraping completed!")
        print(f"Articles found: {len(articles)}")
        
        # Show article details from database
        db = ArticleDB()
        all_articles = db.get_all_articles()
        
        print(f"\nTotal articles in database: {len(all_articles)}")
        if all_articles:
            print("\nMost recent articles:")
            for article in all_articles[:5]:  # Show latest 5 articles
                print(f"\nTitle: {article['title']}")
                print(f"Source: {article['source']}")
                print(f"Date: {article['published_date']}")
                print(f"URL: {article['url']}")
                if article.get('keywords'):
                    print(f"Keywords: {article['keywords']}")
                print("-" * 80)
        
    except Exception as e:
        print(f"Error running scraper: {str(e)}")
        raise

if __name__ == "__main__":
    main()
