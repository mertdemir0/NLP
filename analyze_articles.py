"""Script to analyze scraped articles."""
import json
from src.analysis.article_analyzer import ArticleAnalyzer
from src.database.models import ArticleDB
from src.preprocessing.text_cleaner import TextCleaner
from typing import List, Dict
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def preprocess_articles(articles: List[Dict], cleaner: TextCleaner) -> List[Dict]:
    """Preprocess article texts.
    
    Args:
        articles: List of article dictionaries
        cleaner: TextCleaner instance
        
    Returns:
        List of preprocessed article dictionaries
    """
    processed_articles = []
    
    for article in articles:
        try:
            # Clean title and content
            clean_title = cleaner.clean_text(article['title'])
            clean_content = cleaner.clean_text(article.get('content', ''))
            
            # Extract named entities
            entities = cleaner.extract_named_entities(article['title'] + ' ' + article.get('content', ''))
            
            # Get sentences for potential summarization
            sentences = cleaner.extract_sentences(article.get('content', ''))
            
            # Create processed article
            processed_article = {
                **article,  # Keep original fields
                'clean_title': clean_title,
                'clean_content': clean_content,
                'named_entities': entities,
                'sentences': sentences
            }
            processed_articles.append(processed_article)
            
        except Exception as e:
            logger.error(f"Error preprocessing article {article.get('title', 'Unknown')}: {str(e)}")
            continue
    
    return processed_articles

def main():
    """Run article analysis."""
    logger.info("Starting article analysis...")
    
    # Get articles from database
    db = ArticleDB()
    articles = db.get_all_articles()
    
    if not articles:
        logger.warning("No articles found in database!")
        return
    
    logger.info(f"Found {len(articles)} articles to analyze.")
    
    # Initialize text cleaner with custom nuclear-related stopwords
    nuclear_stopwords = [
        'nuclear', 'energy', 'power', 'plant', 'reactor',  # Too common in our domain
        'said', 'says', 'told', 'according',  # Reporting words
        'monday', 'tuesday', 'wednesday', 'thursday', 'friday'  # Days
    ]
    
    cleaner = TextCleaner(
        remove_urls=True,
        remove_numbers=False,  # Keep numbers as they might be important in nuclear context
        remove_punctuation=True,
        convert_lowercase=True,
        remove_stopwords=True,
        lemmatize=True,
        min_token_length=3,
        custom_stopwords=nuclear_stopwords
    )
    
    # Preprocess articles
    logger.info("Preprocessing articles...")
    processed_articles = preprocess_articles(articles, cleaner)
    logger.info(f"Successfully preprocessed {len(processed_articles)} articles")
    
    # Initialize analyzer and generate report
    logger.info("Generating analysis report...")
    analyzer = ArticleAnalyzer()
    report = analyzer.generate_report(processed_articles)
    
    logger.info("\nAnalysis Report:")
    print(report)
    
    logger.info("\nAnalysis complete! Check data/analysis directory for visualizations and full report.")

if __name__ == "__main__":
    main()
