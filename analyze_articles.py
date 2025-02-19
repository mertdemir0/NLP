"""Script to analyze scraped articles."""
import json
from src.analysis.article_analyzer import ArticleAnalyzer
from src.database.models import ArticleDB

def main():
    """Run article analysis."""
    print("Starting article analysis...")
    
    # Get articles from database
    db = ArticleDB()
    articles = db.get_all_articles()
    
    if not articles:
        print("No articles found in database!")
        return
    
    print(f"Found {len(articles)} articles to analyze.")
    
    # Initialize analyzer and generate report
    analyzer = ArticleAnalyzer()
    report = analyzer.generate_report(articles)
    
    print("\nAnalysis Report:")
    print(report)
    
    print("\nAnalysis complete! Check data/analysis directory for visualizations and full report.")

if __name__ == "__main__":
    main()
