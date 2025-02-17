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
from .preprocessing import TextCleaner, Tokenizer, Normalizer
from .analysis import (
    SentimentAnalyzer,
    TopicModeler,
    SemanticAnalyzer,
    TemporalAnalyzer,
    GeoAnalyzer
)
from .visualization import NuclearEnergyDashboard, ReportGenerator

logger = logging.getLogger(__name__)

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

def run_pipeline(config: Dict, input_dir: str, output_dir: str) -> Dict:
    """
    Run the complete analysis pipeline.
    
    Args:
        config: Configuration dictionary
        input_dir: Input directory path
        output_dir: Output directory path
        
    Returns:
        Dictionary containing analysis results
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize components
    ingestion = DataIngestion(config)
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
    
    # Ingest data
    logger.info("Starting data ingestion...")
    results = ingestion.ingest_directory(input_dir)
    ingestion.save_results(results, os.path.join(output_dir, 'raw'))
    
    # Preprocess texts
    logger.info("Preprocessing texts...")
    processed_texts = []
    for result in results:
        if result['success']:
            text = result['text']
            text = text_cleaner.clean(text)
            tokens = tokenizer.tokenize(text)
            normalized = normalizer.normalize(tokens)
            processed_texts.append({
                'text': text,
                'tokens': tokens,
                'normalized': normalized,
                'metadata': result['metadata']
            })
    
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
    config = load_config(args.config)
    
    try:
        # Run pipeline
        results = run_pipeline(config, args.input_dir, args.output_dir)
        
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