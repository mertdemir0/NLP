import sqlite3
import pandas as pd
from pathlib import Path
from src.analysis.sentiment_analysis import SentimentAnalyzer
from src.analysis.geo_analysis import GeoAnalyzer
from src.analysis.temporal_analysis import TemporalAnalyzer
from src.analysis.visualization import VisualizationManager
from collections import Counter
import re
from datetime import datetime, timedelta

class DatabaseAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path
        self.sentiment_analyzer = SentimentAnalyzer()
        self.geo_analyzer = GeoAnalyzer()
        self.temporal_analyzer = TemporalAnalyzer()
        self.viz_manager = VisualizationManager()
    
    def parse_relative_date(self, date_str: str) -> datetime:
        """Parse relative date strings like '6 days ago' into datetime objects."""
        if not isinstance(date_str, str):
            return date_str
            
        now = datetime.now()
        
        # Handle 'days ago'
        match = re.match(r'(\d+)\s*days?\s*ago', date_str)
        if match:
            days = int(match.group(1))
            return now - timedelta(days=days)
            
        # Handle 'hours ago'
        match = re.match(r'(\d+)\s*hours?\s*ago', date_str)
        if match:
            hours = int(match.group(1))
            return now - timedelta(hours=hours)
            
        # Handle 'minutes ago'
        match = re.match(r'(\d+)\s*minutes?\s*ago', date_str)
        if match:
            minutes = int(match.group(1))
            return now - timedelta(minutes=minutes)
            
        # If no pattern matches, try pandas to_datetime
        try:
            return pd.to_datetime(date_str)
        except:
            return None
    
    def read_iaea_data(self):
        """
        Read IAEA table data from the database
        Returns DataFrame with title, content, date, and type columns
        """
        query = """
        SELECT title, content, date, type 
        FROM IAEA
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn)
                # Convert dates
                df['date'] = pd.to_datetime(df['date'])
                return df
        except Exception as e:
            print(f"Error reading IAEA data: {e}")
            return None

    def read_bloomberg_data(self):
        """
        Read Bloomberg table data from the database
        Returns DataFrame with title and summary columns
        """
        query = """
        SELECT title, summary, date 
        FROM Bloomberg
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn)
                # Parse relative dates
                df['date'] = df['date'].apply(self.parse_relative_date)
                # Drop rows with invalid dates
                df = df.dropna(subset=['date'])
                return df
        except Exception as e:
            print(f"Error reading Bloomberg data: {e}")
            return None

    def analyze_iaea_data(self, df):
        """
        Perform comprehensive analysis on IAEA data
        """
        if df is None or df.empty:
            return
        
        print("\nIAEA Data Analysis:")
        print(f"Total number of articles: {len(df)}")
        print("\nArticle types distribution:")
        print(df['type'].value_counts())
        print("\nDate range:")
        df['date'] = pd.to_datetime(df['date'])
        print(f"From: {df['date'].min()}")
        print(f"To: {df['date'].max()}")

        # Temporal Analysis
        articles = df.to_dict('records')
        temporal_results = self.temporal_analyzer.analyze_content_volume(articles)
        print("\nTemporal Analysis:")
        print(temporal_results)

        # Sentiment Analysis
        texts = df['content'].tolist()
        sentiment_results = self.sentiment_analyzer.analyze_temporal_trends(texts, df['date'].tolist())
        print("\nSentiment Analysis:")
        print(sentiment_results)

        # Geographical Analysis
        geo_results = self.geo_analyzer.analyze_articles(articles)
        print("\nGeographical Analysis:")
        print(geo_results)

    def analyze_bloomberg_data(self, df):
        """
        Perform comprehensive analysis on Bloomberg data
        """
        if df is None or df.empty:
            return
        
        print("\nBloomberg Data Analysis:")
        print(f"Total number of articles: {len(df)}")
        
        # Sentiment Analysis on summaries
        texts = df['summary'].tolist()
        sentiment_results = self.sentiment_analyzer.analyze_temporal_trends(texts, df['date'].tolist())
        print("\nSentiment Analysis:")
        print(sentiment_results)

        # Geographical Analysis
        articles = df.to_dict('records')
        geo_results = self.geo_analyzer.analyze_articles(articles)
        print("\nGeographical Analysis:")
        print(geo_results)

    def generate_reports(self, iaea_df: pd.DataFrame, bloomberg_df: pd.DataFrame):
        """Generate comprehensive analysis reports and visualizations."""
        # Prepare temporal data
        iaea_temporal = self.temporal_analyzer.analyze_content_volume(
            iaea_df.to_dict('records')
        )
        temporal_df = pd.DataFrame([
            {'date': k, 'value': v, 'source': 'IAEA'}
            for k, v in iaea_temporal['volume_over_time'].items()
        ])
        
        if bloomberg_df is not None:
            bloomberg_temporal = self.temporal_analyzer.analyze_content_volume(
                bloomberg_df.to_dict('records')
            )
            temporal_df = pd.concat([
                temporal_df,
                pd.DataFrame([
                    {'date': k, 'value': v, 'source': 'Bloomberg'}
                    for k, v in bloomberg_temporal['volume_over_time'].items()
                ])
            ])
        
        # Prepare sentiment data
        iaea_sentiment = []
        for _, row in iaea_df.iterrows():
            sentiment = self.sentiment_analyzer.analyze_sentiment(row['content'])
            iaea_sentiment.append({
                'date': row['date'],
                'sentiment': sentiment['score'],
                'source': 'IAEA'
            })
        
        sentiment_df = pd.DataFrame(iaea_sentiment)
        
        if bloomberg_df is not None:
            bloomberg_sentiment = []
            for _, row in bloomberg_df.iterrows():
                sentiment = self.sentiment_analyzer.analyze_sentiment(row['summary'])
                bloomberg_sentiment.append({
                    'date': row['date'],
                    'sentiment': sentiment['score'],
                    'source': 'Bloomberg'
                })
            sentiment_df = pd.concat([
                sentiment_df,
                pd.DataFrame(bloomberg_sentiment)
            ])
        
        # Round dates to months for better visualization
        sentiment_df['date'] = sentiment_df['date'].dt.to_period('M').astype(str)
        
        # Prepare technology data
        iaea_tech = pd.DataFrame([
            {'technology': tech, 'count': count, 'source': 'IAEA'}
            for tech, count in Counter(
                tech
                for text in iaea_df['content']
                for tech in self.temporal_analyzer.classify_technology(text)
            ).items()
        ])
        
        if bloomberg_df is not None:
            bloomberg_tech = pd.DataFrame([
                {'technology': tech, 'count': count, 'source': 'Bloomberg'}
                for tech, count in Counter(
                    tech
                    for text in bloomberg_df['summary']
                    for tech in self.temporal_analyzer.classify_technology(text)
                ).items()
            ])
            tech_df = pd.concat([iaea_tech, bloomberg_tech])
        else:
            tech_df = iaea_tech
        
        # Create visualizations
        temporal_fig = self.viz_manager.create_temporal_plot(
            temporal_df,
            'date',
            'value',
            'Content Volume Over Time'
        )
        
        sentiment_fig = self.viz_manager.create_sentiment_heatmap(
            sentiment_df,
            'date',
            'source',
            'sentiment',
            'Sentiment Analysis Over Time'
        )
        
        tech_fig = self.viz_manager.create_technology_comparison(
            tech_df,
            tech_col='technology',
            value_col='count',
            source_col='source'
        )
        
        # Create interactive dashboard
        app = self.viz_manager.create_dashboard(
            temporal_fig=temporal_fig,
            sentiment_fig=sentiment_fig,
            tech_fig=tech_fig,
            title="Nuclear Energy Content Analysis Dashboard"
        )
        
        return app

if __name__ == "__main__":
    # Set the path to your database
    db_path = Path("data/db/IAEA.db")
    
    # Initialize analyzer
    analyzer = DatabaseAnalyzer(db_path)
    
    # Read data
    iaea_df = analyzer.read_iaea_data()
    bloomberg_df = analyzer.read_bloomberg_data()
    
    # Generate reports and start dashboard
    app = analyzer.generate_reports(iaea_df, bloomberg_df)
    app.run_server(debug=True)
