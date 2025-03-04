#!/usr/bin/env python3
"""Script to analyze Bloomberg nuclear articles from the database."""
import argparse
import logging
import os
import sqlite3
import json
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Download NLTK resources
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Bloomberg Nuclear Articles Analyzer')
    
    parser.add_argument('--db-path', type=str, default='data/bloomberg_nuclear.db',
                        help='Path to SQLite database (default: data/bloomberg_nuclear.db)')
    
    parser.add_argument('--output-dir', type=str, default='data/analysis',
                        help='Directory to store analysis results (default: data/analysis)')
    
    parser.add_argument('--start-date', type=str,
                        help='Start date for analysis in YYYY-MM-DD format (default: all dates)')
    
    parser.add_argument('--end-date', type=str,
                        help='End date for analysis in YYYY-MM-DD format (default: all dates)')
    
    return parser.parse_args()

def load_data(db_path, start_date=None, end_date=None):
    """Load articles from the database.
    
    Args:
        db_path: Path to SQLite database
        start_date: Start date for filtering (optional)
        end_date: End date for filtering (optional)
        
    Returns:
        pandas.DataFrame: DataFrame containing articles
    """
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        
        # Build the query
        query = "SELECT * FROM articles"
        params = []
        
        if start_date and end_date:
            query += " WHERE date BETWEEN ? AND ?"
            params = [start_date, end_date]
        elif start_date:
            query += " WHERE date >= ?"
            params = [start_date]
        elif end_date:
            query += " WHERE date <= ?"
            params = [end_date]
        
        # Load data into DataFrame
        df = pd.read_sql_query(query, conn, params=params)
        
        # Close the connection
        conn.close()
        
        # Parse dates
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        if 'publish_date' in df.columns:
            df['publish_date'] = pd.to_datetime(df['publish_date'], errors='coerce')
        
        # Parse JSON columns
        if 'authors' in df.columns:
            df['authors'] = df['authors'].apply(lambda x: json.loads(x) if isinstance(x, str) else [])
        
        if 'keywords' in df.columns:
            df['keywords'] = df['keywords'].apply(lambda x: json.loads(x) if isinstance(x, str) else [])
        
        logger.info(f"Loaded {len(df)} articles from database")
        return df
    
    except (sqlite3.Error, pd.errors.DatabaseError) as e:
        logger.error(f"Error loading data from database: {str(e)}")
        return pd.DataFrame()

def analyze_time_distribution(df, output_dir):
    """Analyze the time distribution of articles.
    
    Args:
        df: DataFrame containing articles
        output_dir: Directory to save output files
    """
    if df.empty or 'date' not in df.columns:
        logger.warning("Cannot analyze time distribution: DataFrame is empty or missing date column")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Group by year and month
        df['year_month'] = df['date'].dt.to_period('M')
        monthly_counts = df.groupby('year_month').size()
        
        # Convert to DataFrame for plotting
        monthly_df = monthly_counts.reset_index()
        monthly_df.columns = ['Year-Month', 'Article Count']
        monthly_df['Year-Month'] = monthly_df['Year-Month'].astype(str)
        
        # Plot monthly distribution
        plt.figure(figsize=(15, 8))
        sns.barplot(x='Year-Month', y='Article Count', data=monthly_df)
        plt.xticks(rotation=90)
        plt.title('Monthly Distribution of Bloomberg Nuclear Articles')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'monthly_distribution.png'))
        plt.close()
        
        # Save to CSV
        monthly_df.to_csv(os.path.join(output_dir, 'monthly_distribution.csv'), index=False)
        
        logger.info(f"Time distribution analysis saved to {output_dir}")
    
    except Exception as e:
        logger.error(f"Error analyzing time distribution: {str(e)}")

def analyze_content(df, output_dir):
    """Analyze the content of articles.
    
    Args:
        df: DataFrame containing articles
        output_dir: Directory to save output files
    """
    if df.empty or 'text' not in df.columns:
        logger.warning("Cannot analyze content: DataFrame is empty or missing text column")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Combine all text
        all_text = ' '.join(df['text'].fillna(''))
        
        # Tokenize and clean text
        stop_words = set(stopwords.words('english'))
        additional_stop_words = {'said', 'would', 'could', 'also', 'according', 'year', 'years', 'one', 'two', 'three', 'new', 'time', 'bloomberg'}
        stop_words.update(additional_stop_words)
        
        # Clean text
        clean_text = re.sub(r'[^\w\s]', ' ', all_text.lower())
        tokens = word_tokenize(clean_text)
        filtered_tokens = [word for word in tokens if word.isalpha() and word not in stop_words and len(word) > 2]
        
        # Count word frequencies
        word_freq = Counter(filtered_tokens)
        most_common = word_freq.most_common(50)
        
        # Save word frequencies to CSV
        word_freq_df = pd.DataFrame(most_common, columns=['Word', 'Frequency'])
        word_freq_df.to_csv(os.path.join(output_dir, 'word_frequencies.csv'), index=False)
        
        # Generate word cloud
        wordcloud = WordCloud(width=800, height=400, background_color='white', max_words=100).generate(' '.join(filtered_tokens))
        
        plt.figure(figsize=(16, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('Word Cloud of Bloomberg Nuclear Articles')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'wordcloud.png'))
        plt.close()
        
        # Plot top 20 words
        plt.figure(figsize=(12, 8))
        top_words_df = pd.DataFrame(word_freq.most_common(20), columns=['Word', 'Frequency'])
        sns.barplot(x='Frequency', y='Word', data=top_words_df)
        plt.title('Top 20 Words in Bloomberg Nuclear Articles')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'top_words.png'))
        plt.close()
        
        logger.info(f"Content analysis saved to {output_dir}")
    
    except Exception as e:
        logger.error(f"Error analyzing content: {str(e)}")

def analyze_keywords(df, output_dir):
    """Analyze article keywords.
    
    Args:
        df: DataFrame containing articles
        output_dir: Directory to save output files
    """
    if df.empty or 'keywords' not in df.columns:
        logger.warning("Cannot analyze keywords: DataFrame is empty or missing keywords column")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Extract all keywords
        all_keywords = []
        for keywords_list in df['keywords']:
            if isinstance(keywords_list, list):
                all_keywords.extend(keywords_list)
        
        # Count keyword frequencies
        keyword_freq = Counter(all_keywords)
        most_common = keyword_freq.most_common(50)
        
        # Save keyword frequencies to CSV
        keyword_freq_df = pd.DataFrame(most_common, columns=['Keyword', 'Frequency'])
        keyword_freq_df.to_csv(os.path.join(output_dir, 'keyword_frequencies.csv'), index=False)
        
        # Plot top 20 keywords
        plt.figure(figsize=(12, 8))
        top_keywords_df = pd.DataFrame(keyword_freq.most_common(20), columns=['Keyword', 'Frequency'])
        sns.barplot(x='Frequency', y='Keyword', data=top_keywords_df)
        plt.title('Top 20 Keywords in Bloomberg Nuclear Articles')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'top_keywords.png'))
        plt.close()
        
        logger.info(f"Keyword analysis saved to {output_dir}")
    
    except Exception as e:
        logger.error(f"Error analyzing keywords: {str(e)}")

def generate_summary_report(df, output_dir):
    """Generate a summary report of the analysis.
    
    Args:
        df: DataFrame containing articles
        output_dir: Directory to save output files
    """
    if df.empty:
        logger.warning("Cannot generate summary report: DataFrame is empty")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Basic statistics
        total_articles = len(df)
        date_range = f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}" if 'date' in df.columns and not df['date'].isna().all() else "Unknown"
        avg_length = df['text'].str.len().mean() if 'text' in df.columns else 0
        
        # Create summary report
        report = f"""# Bloomberg Nuclear Articles Analysis Summary

## Overview
- **Total Articles**: {total_articles}
- **Date Range**: {date_range}
- **Average Article Length**: {avg_length:.0f} characters

## Time Distribution
The monthly distribution of articles is available in the file `monthly_distribution.csv` and visualized in `monthly_distribution.png`.

## Content Analysis
The most frequent words in the articles are available in the file `word_frequencies.csv` and visualized in `wordcloud.png` and `top_words.png`.

## Keyword Analysis
The most frequent keywords are available in the file `keyword_frequencies.csv` and visualized in `top_keywords.png`.

## Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Save report
        with open(os.path.join(output_dir, 'summary_report.md'), 'w') as f:
            f.write(report)
        
        logger.info(f"Summary report saved to {os.path.join(output_dir, 'summary_report.md')}")
    
    except Exception as e:
        logger.error(f"Error generating summary report: {str(e)}")

def main():
    """Run the Bloomberg nuclear articles analyzer."""
    args = parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    logger.info(f"Starting Bloomberg nuclear articles analyzer")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Output directory: {args.output_dir}")
    
    # Load data
    df = load_data(args.db_path, args.start_date, args.end_date)
    
    if df.empty:
        logger.error("No articles found in the database")
        return
    
    # Run analyses
    analyze_time_distribution(df, args.output_dir)
    analyze_content(df, args.output_dir)
    analyze_keywords(df, args.output_dir)
    generate_summary_report(df, args.output_dir)
    
    logger.info(f"Analysis complete! Results saved to {args.output_dir}")

if __name__ == "__main__":
    main() 