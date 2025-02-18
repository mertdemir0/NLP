"""
Main entry point for nuclear energy content analysis pipeline.
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .utils import setup_logging, load_config
from .data_ingestion import DataIngestion
from .utils.config import Config
from .utils.logger import Logger
from .data_ingestion.news_scraper import NewsScraper
from .preprocessing import TextCleaner, Tokenizer, Normalizer
from .analysis import (
    SentimentAnalyzer,
    TopicModeler,
    SemanticAnalyzer,
    TemporalAnalyzer,
    GeoAnalyzer
)
from .visualization import NuclearEnergyDashboard, ReportGenerator

logger = Logger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Nuclear Energy Content Analysis Pipeline'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--input-dir',
        type=str,
        help='Directory containing input files'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='Directory for output files'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to look back for articles'
    )
    
    parser.add_argument(
        '--query',
        type=str,
        default='nuclear energy',
        help='Search query for articles'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Logging level'
    )
    
    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='Launch interactive dashboard'
    )
    
    return parser.parse_args()

def run_pipeline(config: Dict, query: str, days: int, output_dir: str) -> Dict:
    """
    Run the complete analysis pipeline.
    
    Args:
        config: Configuration dictionary
        input_dir: Input directory path
        query: Search query for articles
        days: Number of days to look back
        output_dir: Output directory path
        
    Returns:
        Dictionary containing analysis results
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    raw_dir = os.path.join(output_dir, 'raw')
    processed_dir = os.path.join(output_dir, 'processed')
    
    # Initialize components
    ingestion = DataIngestion(config)
    scraper = NewsScraper(config)
    text_cleaner = TextCleaner()
    tokenizer = Tokenizer()
    normalizer = Normalizer()
    
    analyzers = {
        'sentiment': SentimentAnalyzer(),
        'topic': TopicModeler(),
        'semantic': SemanticAnalyzer(),
        'temporal': TemporalAnalyzer(),
        'geo': GeoAnalyzer()
    }
    
    # Scrape articles
    logger.info(f"Scraping articles for query: {query} (last {days} days)...")
    results = ingestion.ingest_directory(input_dir)
    ingestion.save_results(results, os.path.join(output_dir, 'raw'))
    articles = scraper.run(query=query, days=days, output_dir=raw_dir)
    
    # Preprocess texts
    logger.info("Preprocessing articles...")
    processed_texts = []
    for article in articles:
        try:
            text = article['text']
            text = text_cleaner.clean(text)
            tokens = tokenizer.tokenize(text)
            normalized = normalizer.normalize(tokens)
            
            processed_texts.append({
                'text': text,
                'tokens': tokens,
                'normalized': normalized,
                'metadata': {
                    'title': article['title'],
                    'url': article['url'],
                    'date': article['date'],
                    'source': article['source']
                }
            })
        except Exception as e:
            logger.error(f"Error processing article: {str(e)}")
            continue
    
    # Run analysis
    logger.info("Running analysis...")
    analysis_results = {}
    
    for name, analyzer in analyzers.items():
        logger.info(f"Running {name} analysis...")
        try:
            results = analyzer.analyze(processed_texts)
            analysis_results[name] = results
        except Exception as e:
            logger.error(f"Error in {name} analysis: {str(e)}")
            analysis_results[name] = {'error': str(e)}
    
    # Generate visualizations and reports
    logger.info("Generating reports...")
    report_generator = ReportGenerator(config)
    report_generator.generate_report(analysis_results, output_dir)
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'analysis_results_{timestamp}.json')
    
    return analysis_results

def main():
    """Main function."""
    # Parse arguments
    args = parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Load configuration
    config = Config()
    
    try:
        # Run pipeline
        results = run_pipeline(
            config=config.get_all_configs(),
            query=args.query,
            days=args.days,
            output_dir=args.output_dir
        )
        
        # Launch dashboard if requested
        if args.dashboard:
            logger.info("Launching dashboard...")
            dashboard = NuclearEnergyDashboard(config)
            dashboard.load_data(args.output_dir)
            dashboard.run()
            
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()