"""Script to analyze scraped articles."""
import json
from src.analysis.article_analyzer import ArticleAnalyzer
from src.database.models import ArticleDB
from src.preprocessing.text_cleaner import TextCleaner
from typing import List, Dict, Generator
import logging
from tqdm import tqdm
import pandas as pd
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def batch_generator(items: List[Dict], batch_size: int) -> Generator[List[Dict], None, None]:
    """Generate batches from items.
    
    Args:
        items: List of items to batch
        batch_size: Size of each batch
        
    Yields:
        Batch of items
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]

def preprocess_articles(articles: List[Dict], cleaner: TextCleaner) -> List[Dict]:
    """Preprocess article texts.
    
    Args:
        articles: List of article dictionaries
        cleaner: TextCleaner instance
        
    Returns:
        List of preprocessed article dictionaries
    """
    processed_articles = []
    
    for article in tqdm(articles, desc="Preprocessing articles"):
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
                'sentences': sentences,
                'source_db': article.get('source_db', 'unknown')  # Track which database the article came from
            }
            processed_articles.append(processed_article)
            
        except Exception as e:
            logger.error(f"Error preprocessing article {article.get('title', 'Unknown')}: {str(e)}")
            continue
    
    return processed_articles

def analyze_by_source(articles: List[Dict], analyzer: ArticleAnalyzer) -> None:
    """Analyze articles separately for each source database.
    
    Args:
        articles: List of preprocessed articles
        analyzer: ArticleAnalyzer instance
    """
    # Split articles by source
    bloomberg_articles = [a for a in articles if a.get('source_db') == 'Bloomberg']
    iaea_articles = [a for a in articles if a.get('source_db') == 'IAEA']
    
    # Analyze Bloomberg articles
    if bloomberg_articles:
        logger.info(f"\nAnalyzing {len(bloomberg_articles)} Bloomberg articles...")
        report = analyzer.generate_report(bloomberg_articles)
        
        # Save Bloomberg report
        with open('data/analysis/bloomberg_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
    
    # Analyze IAEA articles
    if iaea_articles:
        logger.info(f"\nAnalyzing {len(iaea_articles)} IAEA articles...")
        report = analyzer.generate_report(iaea_articles)
        
        # Save IAEA report
        with open('data/analysis/iaea_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
    
    # Combined analysis
    logger.info("\nGenerating combined analysis...")
    report = analyzer.generate_report(articles)
    with open('data/analysis/combined_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

def main():
    """Run article analysis."""
    logger.info("Starting article analysis...")
    
    # Get articles from database
    db = ArticleDB()
    
    # Get articles from both tables
    bloomberg_articles = db.get_bloomberg_articles()
    iaea_articles = db.get_iaea_articles()
    
    # Add source database information
    for article in bloomberg_articles:
        article['source_db'] = 'Bloomberg'
    for article in iaea_articles:
        article['source_db'] = 'IAEA'
    
    # Combine articles
    all_articles = bloomberg_articles + iaea_articles
    
    if not all_articles:
        logger.warning("No articles found in database!")
        return
    
    logger.info(f"Found {len(all_articles)} total articles to analyze:")
    logger.info(f"- Bloomberg: {len(bloomberg_articles)} articles")
    logger.info(f"- IAEA: {len(iaea_articles)} articles")
    
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
    
    # Process articles in batches
    batch_size = 100
    processed_articles = []
    
    logger.info("Processing articles in batches...")
    for batch in tqdm(batch_generator(all_articles, batch_size), total=len(all_articles)//batch_size + 1):
        processed_batch = preprocess_articles(batch, cleaner)
        processed_articles.extend(processed_batch)
    
    logger.info(f"Successfully preprocessed {len(processed_articles)} articles")
    
    # Initialize analyzer
    analyzer = ArticleAnalyzer()
    
    # Analyze articles by source and combined
    analyze_by_source(processed_articles, analyzer)
    
    logger.info("\nAnalysis complete! Check data/analysis directory for reports and visualizations:")
    logger.info("- bloomberg_report.md: Analysis of Bloomberg articles")
    logger.info("- iaea_report.md: Analysis of IAEA articles")
    logger.info("- combined_report.md: Combined analysis of all articles")

if __name__ == "__main__":
    main()
