"""
Sentiment analysis for nuclear energy content.
"""
from typing import List, Dict, Any
import pandas as pd
from transformers import pipeline, AutoTokenizer
from src.analysis.base_analyzer import BaseAnalyzer
import logging
import numpy as np

logger = logging.getLogger(__name__)

class SentimentAnalyzer(BaseAnalyzer):
    """Analyzer for sentiment analysis of nuclear energy content."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the sentiment analyzer."""
        super().__init__(config_path)
        self.model_name = "distilbert-base-uncased-finetuned-sst-2-english"
        self.sentiment_pipeline = pipeline("sentiment-analysis", model=self.model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.max_length = 512  # Maximum sequence length for DistilBERT
        
    def _truncate_text(self, text: str) -> str:
        """Truncate text to fit within model's maximum sequence length."""
        tokens = self.tokenizer.tokenize(text)
        if len(tokens) > self.max_length - 2:  # Account for [CLS] and [SEP] tokens
            tokens = tokens[:(self.max_length - 2)]
            logger.debug(f"Truncated text from {len(tokens)} tokens to {self.max_length}")
        return self.tokenizer.convert_tokens_to_string(tokens)
    
    def _chunk_and_analyze(self, text: str) -> float:
        """Split long text into chunks and average their sentiment scores."""
        # Split text into sentences (rough approximation)
        chunks = [s.strip() for s in text.split('.') if s.strip()]
        
        if not chunks:
            return 0.0
        
        # Initialize variables for weighted average
        total_score = 0
        total_length = 0
        
        # Process each chunk
        for chunk in chunks:
            truncated_chunk = self._truncate_text(chunk)
            if not truncated_chunk:
                continue
                
            try:
                result = self.sentiment_pipeline(truncated_chunk)[0]
                # Convert sentiment to numeric score (-1 for negative, 1 for positive)
                score = 1 if result['label'] == 'POSITIVE' else -1
                # Weight by chunk length
                chunk_length = len(chunk.split())
                total_score += score * chunk_length
                total_length += chunk_length
            except Exception as e:
                logger.warning(f"Error processing chunk: {str(e)}")
                continue
        
        # Return weighted average score
        return total_score / total_length if total_length > 0 else 0.0
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of a text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dictionary containing sentiment analysis results
        """
        try:
            sentiment_score = self._chunk_and_analyze(text)
            
            return {
                'score': sentiment_score,
                'label': 'POSITIVE' if sentiment_score > 0 else 'NEGATIVE',
                'confidence': abs(sentiment_score)
            }
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return {'score': 0, 'label': 'NEUTRAL', 'confidence': 0}
    
    def analyze_by_technology(self, texts: List[str], technologies: List[List[str]]) -> pd.DataFrame:
        """Analyze sentiment grouped by technology.
        
        Args:
            texts: List of article texts
            technologies: List of technology categories for each text
            
        Returns:
            DataFrame with sentiment scores by technology
        """
        results = []
        for text, techs in zip(texts, technologies):
            sentiment = self.analyze_sentiment(text)
            for tech in techs:
                results.append({
                    'technology': tech,
                    'sentiment': sentiment['score'],
                    'label': sentiment['label']
                })
        
        return pd.DataFrame(results)
    
    def analyze_temporal_trends(self, texts: List[str], dates: List[str]) -> pd.DataFrame:
        """Analyze sentiment trends over time.
        
        Args:
            texts: List of article texts
            dates: List of article dates
            
        Returns:
            DataFrame with sentiment scores over time
        """
        results = []
        for text, date in zip(texts, dates):
            sentiment = self.analyze_sentiment(text)
            results.append({
                'date': pd.to_datetime(date),
                'sentiment': sentiment['score'],
                'label': sentiment['label']
            })
        
        return pd.DataFrame(results)
    
    def analyze_geographical_sentiment(self, texts: List[str], locations: List[str]) -> pd.DataFrame:
        """Analyze sentiment by geographical location.
        
        Args:
            texts: List of article texts
            locations: List of locations mentioned in texts
            
        Returns:
            DataFrame with sentiment scores by location
        """
        results = []
        for text, location in zip(texts, locations):
            if location:  # Only analyze if location is present
                sentiment = self.analyze_sentiment(text)
                results.append({
                    'location': location,
                    'sentiment': sentiment['score'],
                    'label': sentiment['label']
                })
        
        return pd.DataFrame(results)
    
    def get_summary_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate summary statistics for sentiment analysis.
        
        Args:
            df: DataFrame with sentiment analysis results
            
        Returns:
            Dictionary with summary statistics
        """
        return {
            'overall_sentiment': df['sentiment'].mean(),
            'sentiment_std': df['sentiment'].std(),
            'positive_ratio': (df['label'] == 'POSITIVE').mean(),
            'by_technology': df.groupby('technology')['sentiment'].agg(['mean', 'std']).to_dict(),
            'temporal_trend': df.groupby(df['date'].dt.to_period('M'))['sentiment'].mean().to_dict()
        }

def main():
    """Main function to demonstrate usage."""
    analyzer = SentimentAnalyzer()
    analyzer.load_data()
    
    if analyzer.data is not None:
        # Example analysis
        texts = analyzer.data['content'].tolist()
        dates = analyzer.data['date'].tolist()
        technologies = [analyzer.classify_technology(text) for text in texts]
        
        # Analyze sentiment by technology
        tech_sentiment = analyzer.analyze_by_technology(texts, technologies)
        
        # Analyze temporal trends
        temporal_sentiment = analyzer.analyze_temporal_trends(texts, dates)
        
        # Get summary statistics
        summary = analyzer.get_summary_statistics(tech_sentiment)
        
        # Save results
        analyzer.save_results({
            'technology_sentiment': tech_sentiment.to_dict(),
            'temporal_sentiment': temporal_sentiment.to_dict(),
            'summary_statistics': summary
        })

if __name__ == "__main__":
    main()