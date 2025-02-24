"""
Sentiment analysis for nuclear energy content.
"""
from typing import List, Dict, Any
import pandas as pd
from transformers import pipeline
from src.analysis.base_analyzer import BaseAnalyzer

class SentimentAnalyzer(BaseAnalyzer):
    """Analyzer for sentiment analysis of nuclear energy content."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the sentiment analyzer."""
        super().__init__(config_path)
        self.sentiment_pipeline = None
        
    def initialize_model(self) -> None:
        """Initialize the sentiment analysis model."""
        self.sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model=self.config['analysis']['sentiment']['model']
        )
    
    def analyze_by_technology(self, texts: List[str], technologies: List[List[str]]) -> pd.DataFrame:
        """Analyze sentiment grouped by technology.
        
        Args:
            texts: List of article texts
            technologies: List of technology categories for each text
            
        Returns:
            DataFrame with sentiment scores by technology
        """
        if self.sentiment_pipeline is None:
            self.initialize_model()
            
        results = []
        for text, techs in zip(texts, technologies):
            sentiment = self.sentiment_pipeline(text)[0]
            for tech in techs:
                results.append({
                    'technology': tech,
                    'sentiment': sentiment['score'] if sentiment['label'] == 'POSITIVE' else -sentiment['score'],
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
        if self.sentiment_pipeline is None:
            self.initialize_model()
            
        results = []
        for text, date in zip(texts, dates):
            sentiment = self.sentiment_pipeline(text)[0]
            results.append({
                'date': pd.to_datetime(date),
                'sentiment': sentiment['score'] if sentiment['label'] == 'POSITIVE' else -sentiment['score'],
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
        if self.sentiment_pipeline is None:
            self.initialize_model()
            
        results = []
        for text, location in zip(texts, locations):
            if location:  # Only analyze if location is present
                sentiment = self.sentiment_pipeline(text)[0]
                results.append({
                    'location': location,
                    'sentiment': sentiment['score'] if sentiment['label'] == 'POSITIVE' else -sentiment['score'],
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