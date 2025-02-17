"""
Temporal analysis module for analyzing time-based patterns in nuclear energy content.
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from .base_analyzer import BaseAnalyzer

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
                             time_window: str = 'monthly') -> Dict[str, Dict]:
        """
        Analyze content volume over time.

        Args:
            articles: List of article dictionaries with 'date' and 'text' fields
            time_window: Time window for aggregation ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')

        Returns:
            Dictionary containing temporal analysis results
        """
        if time_window not in self.time_windows:
            raise ValueError(f"Invalid time window. Must be one of {list(self.time_windows.keys())}")

        # Convert dates and create DataFrame
        df = pd.DataFrame([
            {'date': pd.to_datetime(article['date']), 'text': article['text']}
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
                                  time_window: str = 'monthly') -> Dict[str, Dict]:
        """
        Analyze how technology mentions evolve over time.

        Args:
            articles: List of article dictionaries
            time_window: Time window for aggregation

        Returns:
            Dictionary containing technology evolution analysis
        """
        df = pd.DataFrame([
            {
                'date': pd.to_datetime(article['date']),
                'text': article['text'],
                'technology': self.classify_technology(article['text'])
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
                                    time_window: str = 'monthly') -> Dict[str, Dict]:
        """
        Analyze relationships between different aspects over time.

        Args:
            articles: List of article dictionaries
            time_window: Time window for aggregation

        Returns:
            Dictionary containing relationship analysis results
        """
        df = pd.DataFrame([
            {
                'date': pd.to_datetime(article['date']),
                'text': article['text'],
                'technology': self.classify_technology(article['text']),
                'sentiment': self._calculate_sentiment(article['text'])
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
        # Calculate rolling statistics
        rolling_mean = series.rolling(window=3, min_periods=1).mean()
        
        # Calculate growth rates
        growth_rate = (series - series.shift(1)) / series.shift(1)
        
        return {
            'mean': series.mean(),
            'std': series.std(),
            'trend_direction': 1 if growth_rate.mean() > 0 else -1,
            'volatility': growth_rate.std(),
            'last_value': series.iloc[-1],
            'peak_value': series.max()
        }

    def _identify_patterns(self, series: pd.Series) -> Dict[str, List[str]]:
        """Identify temporal patterns in the series."""
        patterns = defaultdict(list)
        
        # Detect seasonality
        if len(series) >= 12:
            seasonal_diff = series - series.shift(12)
            patterns['seasonal'] = bool(seasonal_diff.autocorr() > 0.7)
        
        # Detect trends
        rolling_mean = series.rolling(window=3).mean()
        if rolling_mean.iloc[-1] > rolling_mean.iloc[0]:
            patterns['trend'].append('increasing')
        else:
            patterns['trend'].append('decreasing')
        
        # Detect cycles
        if len(series) >= 4:
            autocorr = [series.autocorr(lag=i) for i in range(1, 5)]
            if any(ac > 0.7 for ac in autocorr):
                patterns['cyclic'] = True
        
        return dict(patterns)

    def _find_peak_periods(self, series: pd.Series) -> List[Dict[str, str]]:
        """Identify peak periods in the time series."""
        # Calculate rolling mean and standard deviation
        rolling_mean = series.rolling(window=3).mean()
        rolling_std = series.rolling(window=3).std()
        
        # Find peaks (periods above mean + 2*std)
        threshold = rolling_mean + (2 * rolling_std)
        peaks = series[series > threshold]
        
        return [
            {
                'date': date.strftime('%Y-%m-%d'),
                'value': value,
                'significance': float((value - rolling_mean[date]) / rolling_std[date])
            }
            for date, value in peaks.items()
        ]

    def _calculate_sentiment(self, text: str) -> float:
        """Calculate sentiment score for text. Override in subclass for better implementation."""
        # This is a placeholder - implement more sophisticated sentiment analysis
        return 0.0