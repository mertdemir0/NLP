"""
Temporal analysis module for analyzing time-based patterns in nuclear energy content.
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from src.analysis.base_analyzer import BaseAnalyzer

class TemporalAnalyzer(BaseAnalyzer):
    """Analyzes temporal patterns in nuclear energy articles."""

    def __init__(self):
        """Initialize the TemporalAnalyzer."""
        super().__init__()
        self.time_windows = {
            'daily': 'D',
            'weekly': 'W',
            'monthly': 'M',
            'quarterly': 'Q',
            'yearly': 'Y'
        }

    def analyze_content_volume(self, articles: List[Dict], 
                             time_window: str = 'monthly',
                             text_field: str = None) -> Dict[str, Dict]:
        """
        Analyze content volume over time.

        Args:
            articles: List of article dictionaries with 'date' and text content field
            time_window: Time window for aggregation ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')
            text_field: Name of the field containing the text content. If None, will try 'content', 'text', or 'summary'

        Returns:
            Dictionary containing temporal analysis results
        """
        if time_window not in self.time_windows:
            raise ValueError(f"Invalid time window. Must be one of {list(self.time_windows.keys())}")

        # Determine which field contains the text content
        if text_field is None:
            if 'content' in articles[0]:
                text_field = 'content'
            elif 'text' in articles[0]:
                text_field = 'text'
            elif 'summary' in articles[0]:
                text_field = 'summary'
            else:
                raise ValueError("Could not find text content field in articles. Expected 'content', 'text', or 'summary'")

        # Convert dates and create DataFrame
        df = pd.DataFrame([
            {'date': pd.to_datetime(article['date']), 'text': article[text_field]}
            for article in articles
        ])

        # Resample and count articles
        volume_series = df.resample(self.time_windows[time_window], on='date').size()

        # Calculate trends and patterns
        trends = self._calculate_trends(volume_series)
        patterns = self._identify_patterns(volume_series)
        peaks = self._find_peak_periods(volume_series)

        return {
            'volume_over_time': volume_series.to_dict(),
            'trends': trends,
            'patterns': patterns,
            'peaks': peaks
        }

    def analyze_technology_evolution(self, articles: List[Dict],
                                  time_window: str = 'monthly',
                                  text_field: str = None) -> Dict[str, Dict]:
        """
        Analyze how technology mentions evolve over time.

        Args:
            articles: List of article dictionaries
            time_window: Time window for aggregation
            text_field: Name of the field containing the text content. If None, will try 'content', 'text', or 'summary'

        Returns:
            Dictionary containing technology evolution analysis
        """
        # Determine which field contains the text content
        if text_field is None:
            if 'content' in articles[0]:
                text_field = 'content'
            elif 'text' in articles[0]:
                text_field = 'text'
            elif 'summary' in articles[0]:
                text_field = 'summary'
            else:
                raise ValueError("Could not find text content field in articles. Expected 'content', 'text', or 'summary'")

        df = pd.DataFrame([
            {
                'date': pd.to_datetime(article['date']),
                'text': article[text_field],
                'technology': self.classify_technology(article[text_field])
            }
            for article in articles
        ])

        # Group by time window and technology
        tech_evolution = df.groupby([
            pd.Grouper(key='date', freq=self.time_windows[time_window]),
            'technology'
        ]).size().unstack(fill_value=0)

        # Calculate technology trends
        tech_trends = {
            tech: self._calculate_trends(tech_evolution[tech])
            for tech in tech_evolution.columns
        }

        return {
            'technology_volume': tech_evolution.to_dict(),
            'technology_trends': tech_trends
        }

    def analyze_temporal_relationships(self, articles: List[Dict],
                                    time_window: str = 'monthly',
                                    text_field: str = None) -> Dict[str, Dict]:
        """
        Analyze relationships between different aspects over time.

        Args:
            articles: List of article dictionaries
            time_window: Time window for aggregation
            text_field: Name of the field containing the text content. If None, will try 'content', 'text', or 'summary'

        Returns:
            Dictionary containing relationship analysis results
        """
        # Determine which field contains the text content
        if text_field is None:
            if 'content' in articles[0]:
                text_field = 'content'
            elif 'text' in articles[0]:
                text_field = 'text'
            elif 'summary' in articles[0]:
                text_field = 'summary'
            else:
                raise ValueError("Could not find text content field in articles. Expected 'content', 'text', or 'summary'")

        df = pd.DataFrame([
            {
                'date': pd.to_datetime(article['date']),
                'text': article[text_field],
                'technology': self.classify_technology(article[text_field]),
                'sentiment': self._calculate_sentiment(article[text_field])
            }
            for article in articles
        ])

        # Analyze sentiment trends by technology
        sentiment_by_tech = df.groupby([
            pd.Grouper(key='date', freq=self.time_windows[time_window]),
            'technology'
        ])['sentiment'].mean().unstack()

        # Find correlations between technologies
        tech_correlations = sentiment_by_tech.corr()

        return {
            'sentiment_trends': sentiment_by_tech.to_dict(),
            'technology_correlations': tech_correlations.to_dict()
        }

    def _calculate_trends(self, series: pd.Series) -> Dict[str, float]:
        """Calculate trend metrics for a time series."""
        # Calculate overall trend (linear regression)
        x = np.arange(len(series))
        y = series.values
        slope, intercept = np.polyfit(x, y, 1)
        
        # Calculate growth rate
        start_val = series.iloc[0]
        end_val = series.iloc[-1]
        growth_rate = ((end_val - start_val) / start_val) if start_val != 0 else 0
        
        # Calculate volatility
        volatility = series.std() / series.mean() if series.mean() != 0 else 0
        
        return {
            'slope': slope,
            'growth_rate': growth_rate,
            'volatility': volatility
        }
    
    def _identify_patterns(self, series: pd.Series) -> Dict[str, List[str]]:
        """Identify temporal patterns in the series."""
        # Calculate moving averages
        ma_short = series.rolling(window=3).mean()
        ma_long = series.rolling(window=6).mean()
        
        # Identify trend periods
        trends = []
        for i in range(len(ma_short)-1):
            if ma_short.iloc[i] < ma_short.iloc[i+1]:
                trends.append('upward')
            else:
                trends.append('downward')
        
        # Identify seasonality
        # Simple approach: compare same months across years
        if len(series) >= 24:  # Need at least 2 years of data
            monthly_avg = series.groupby(series.index.month).mean()
            seasonality = monthly_avg.std() / monthly_avg.mean() > 0.1
        else:
            seasonality = False
        
        return {
            'trends': trends,
            'has_seasonality': seasonality
        }
    
    def _find_peak_periods(self, series: pd.Series) -> List[Dict[str, str]]:
        """Find periods with peak activity."""
        # Calculate threshold for peaks (e.g., 1.5 standard deviations above mean)
        threshold = series.mean() + (1.5 * series.std())
        
        # Find peaks
        peaks = []
        for date, value in series.items():
            if value > threshold:
                peaks.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'value': float(value)
                })
        
        return peaks
    
    def classify_technology(self, text: str) -> str:
        """Classify the technology mentioned in the text."""
        # Define technology keywords
        tech_keywords = {
            'nuclear_fission': ['fission', 'uranium', 'plutonium', 'nuclear reactor', 'nuclear power'],
            'nuclear_fusion': ['fusion', 'tokamak', 'iter', 'plasma', 'magnetic confinement'],
            'smr': ['small modular reactor', 'smr', 'modular nuclear', 'small reactor'],
            'waste_management': ['nuclear waste', 'spent fuel', 'radioactive waste', 'waste storage'],
            'safety_systems': ['containment', 'safety system', 'cooling system', 'emergency core']
        }
        
        # Count mentions of each technology
        tech_counts = defaultdict(int)
        text_lower = text.lower()
        
        for tech, keywords in tech_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    tech_counts[tech] += 1
        
        # Return the most mentioned technology, or 'other' if none found
        if tech_counts:
            return max(tech_counts.items(), key=lambda x: x[1])[0]
        return 'other'

    def _calculate_sentiment(self, text: str) -> float:
        """Calculate sentiment score for text. Override in subclass for better implementation."""
        # This is a placeholder - implement more sophisticated sentiment analysis
        return 0.0