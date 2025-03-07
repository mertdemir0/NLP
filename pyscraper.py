from pygooglenews import GoogleNews
import json
from datetime import datetime, timedelta
import pandas as pd
import os

def get_nuclear_news_by_date_range(start_date, end_date, source='bloomberg.com'):
    """
    Fetch nuclear-related news articles from a specific source within a date range
    Args:
        start_date (str): Start date in YYYY-MM-DD format
        end_date (str): End date in YYYY-MM-DD format
        source (str): News source domain
    """
    try:
        gn = GoogleNews(lang='en')
        print(f"Searching for nuclear news from {source} between {start_date} and {end_date}")
        
        # Construct query with source restriction
        query = f"nuclear site:{source}"
        
        # Search with date range
        search_results = gn.search(query, from_=start_date, to_=end_date)
        
        # Extract relevant information
        articles = []
        entries = search_results.get('entries', [])
        print(f"Found {len(entries)} entries")
        
        for entry in entries:
            article = {
                'title': entry.title,
                'link': entry.link,
                'published': entry.published,
                'published_parsed': datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d'),
                'summary': entry.summary if hasattr(entry, 'summary') else None
            }
            articles.append(article)
            
        return articles
    except Exception as e:
        print(f"Error fetching news: {str(e)}")
        return []

def generate_monthly_ranges(start_date, end_date):
    """Generate a list of monthly date ranges"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    ranges = []
    current = start
    while current < end:
        # Calculate next month
        if current.month == 12:
            next_month = datetime(current.year + 1, 1, 1)
        else:
            next_month = datetime(current.year, current.month + 1, 1)
        
        # Ensure we don't exceed end date
        range_end = min(next_month - timedelta(days=1), end)
        ranges.append((current.strftime('%Y-%m-%d'), range_end.strftime('%Y-%m-%d')))
        current = next_month
    
    return ranges

if __name__ == "__main__":
    START_DATE = '2020-01-01'
    END_DATE = datetime.now().strftime('%Y-%m-%d')
    SOURCE = 'bloomberg.com'
    
    # Create directory for output if it doesn't exist
    output_dir = 'nuclear_news_data'
    os.makedirs(output_dir, exist_ok=True)
    
    # Get monthly ranges
    date_ranges = generate_monthly_ranges(START_DATE, END_DATE)
    
    # Collect all articles
    all_articles = []
    
    for start, end in date_ranges:
        print(f"\nProcessing period: {start} to {end}")
        articles = get_nuclear_news_by_date_range(start, end, SOURCE)
        all_articles.extend(articles)
        
        # Save progress after each month
        df = pd.DataFrame(all_articles)
        if not df.empty:
            output_file = os.path.join(output_dir, 'bloomberg_nuclear_news.csv')
            df.to_csv(output_file, index=False)
            print(f"Saved {len(df)} articles to {output_file}")
    
    # Final summary
    if all_articles:
        print(f"\nTotal articles collected: {len(all_articles)}")
        df = pd.DataFrame(all_articles)
        print("\nArticles per year:")
        print(df['published_parsed'].str[:4].value_counts().sort_index())
    else:
        print("No articles found")