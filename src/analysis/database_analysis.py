import sqlite3
import pandas as pd
from pathlib import Path
from .sentiment_analysis import SentimentAnalyzer
from .geo_analysis import GeoAnalyzer
from .temporal_analysis import TemporalAnalyzer

class DatabaseAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path
        self.sentiment_analyzer = SentimentAnalyzer()
        self.geo_analyzer = GeoAnalyzer()
        self.temporal_analyzer = TemporalAnalyzer()
        
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
        SELECT title, summary 
        FROM Bloomberg
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn)
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

if __name__ == "__main__":
    # Set the path to your database
    db_path = Path("data/db/IAEA.db")
    
    # Initialize analyzer
    analyzer = DatabaseAnalyzer(db_path)
    
    # Read and analyze IAEA data
    iaea_df = analyzer.read_iaea_data()
    analyzer.analyze_iaea_data(iaea_df)
    
    # Read and analyze Bloomberg data
    bloomberg_df = analyzer.read_bloomberg_data()
    analyzer.analyze_bloomberg_data(bloomberg_df)
