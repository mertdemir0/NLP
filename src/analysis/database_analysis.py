import sqlite3
import pandas as pd
from pathlib import Path
from src.analysis.sentiment_analysis import SentimentAnalyzer
from src.analysis.geo_analysis import GeoAnalyzer
from src.analysis.temporal_analysis import TemporalAnalyzer
from src.analysis.visualization import VisualizationManager
from collections import Counter

class DatabaseAnalyzer:
    def __init__(self, db_path):
        self.db_path = db_path
        self.sentiment_analyzer = SentimentAnalyzer()
        self.geo_analyzer = GeoAnalyzer()
        self.temporal_analyzer = TemporalAnalyzer()
        self.viz_manager = VisualizationManager()
        
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
        SELECT title, summary, date 
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
        iaea_sentiment = self.sentiment_analyzer.analyze_temporal_trends(
            iaea_df['content'].tolist(),
            iaea_df['date'].tolist()
        )
        sentiment_df = iaea_sentiment.copy()
        sentiment_df['source'] = 'IAEA'
        
        if bloomberg_df is not None:
            bloomberg_sentiment = self.sentiment_analyzer.analyze_temporal_trends(
                bloomberg_df['summary'].tolist(),
                bloomberg_df['date'].tolist()
            )
            sentiment_df = pd.concat([
                sentiment_df,
                pd.DataFrame({
                    'date': bloomberg_sentiment['date'],
                    'sentiment': bloomberg_sentiment['sentiment'],
                    'source': 'Bloomberg'
                })
            ])
        
        # Prepare technology data
        iaea_tech = pd.DataFrame([
            {'technology': tech, 'count': count, 'source': 'IAEA'}
            for tech, count in Counter(
                self.temporal_analyzer.classify_technology(text)
                for text in iaea_df['content']
            ).items()
        ])
        
        if bloomberg_df is not None:
            bloomberg_tech = pd.DataFrame([
                {'technology': tech, 'count': count, 'source': 'Bloomberg'}
                for tech, count in Counter(
                    self.temporal_analyzer.classify_technology(text)
                    for text in bloomberg_df['summary']
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
        self.viz_manager.save_visualization(temporal_fig, 'temporal_analysis.html')
        
        sentiment_fig = self.viz_manager.create_sentiment_heatmap(
            sentiment_df,
            'date',
            'source',
            'sentiment',
            'Sentiment Analysis Over Time'
        )
        self.viz_manager.save_visualization(sentiment_fig, 'sentiment_analysis.html')
        
        tech_fig = self.viz_manager.create_technology_comparison(tech_df)
        self.viz_manager.save_visualization(tech_fig, 'technology_distribution.html')
        
        # Create interactive dashboard
        app = self.viz_manager.create_dashboard(
            temporal_df,
            sentiment_df,
            tech_df
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
