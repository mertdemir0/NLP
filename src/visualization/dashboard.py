"""
Interactive dashboard for visualizing nuclear energy content analysis.
"""
import os
from typing import Dict, Any, List

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class NuclearEnergyDashboard:
    """Dashboard for visualizing nuclear energy content analysis."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the dashboard.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        self.app = dash.Dash(__name__)
        self.setup_layout()
        
    @staticmethod
    def _load_config(config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def load_data(self, results_dir: str = "output") -> None:
        """Load analysis results."""
        # Load the most recent analysis results
        results_files = [f for f in os.listdir(results_dir) if f.startswith('analysis_results_')]
        if not results_files:
            raise FileNotFoundError("No analysis results found")
            
        latest_results = max(results_files)
        with open(os.path.join(results_dir, latest_results), 'r') as f:
            self.data = yaml.safe_load(f)
    
    def setup_layout(self) -> None:
        """Set up the dashboard layout."""
        self.app.layout = html.Div([
            html.H1("Nuclear Energy Content Analysis Dashboard"),
            
            # Time period selector
            html.Div([
                html.H3("Time Period"),
                dcc.DatePickerRange(
                    id='date-range',
                    start_date=self.config['bloomberg']['start_date'],
                    end_date=self.config['bloomberg']['end_date']
                )
            ]),
            
            # Technology filter
            html.Div([
                html.H3("Technology Focus"),
                dcc.Checklist(
                    id='technology-filter',
                    options=[
                        {'label': cat['name'], 'value': cat['name']}
                        for cat in self.config['analysis']['technology_classification']['categories']
                    ],
                    value=[]
                )
            ]),
            
            # Content volume over time
            html.Div([
                html.H3("Content Volume Over Time"),
                dcc.Graph(id='volume-chart')
            ]),
            
            # Technology distribution
            html.Div([
                html.H3("Technology Distribution"),
                dcc.Graph(id='technology-dist')
            ]),
            
            # Sentiment analysis
            html.Div([
                html.H3("Sentiment Analysis"),
                dcc.Graph(id='sentiment-chart')
            ]),
            
            # Topic modeling
            html.Div([
                html.H3("Topic Distribution"),
                dcc.Graph(id='topic-chart')
            ]),
            
            # Geographical distribution
            html.Div([
                html.H3("Geographical Focus"),
                dcc.Graph(id='geo-chart')
            ])
        ])
    
    def create_volume_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create content volume over time chart."""
        fig = px.line(
            df,
            x='date',
            y='count',
            title='Article Volume Over Time',
            template=self.config['visualization']['plots']['theme']
        )
        return fig
    
    def create_technology_dist(self, data: List[Dict[str, Any]]) -> go.Figure:
        """Create technology distribution chart."""
        fig = px.pie(
            data,
            names='technology',
            values='count',
            title='Distribution of Nuclear Technologies',
            template=self.config['visualization']['plots']['theme']
        )
        return fig
    
    def create_sentiment_chart(self, df: pd.DataFrame) -> go.Figure:
        """Create sentiment analysis chart."""
        fig = px.box(
            df,
            x='technology',
            y='sentiment',
            title='Sentiment Distribution by Technology',
            template=self.config['visualization']['plots']['theme']
        )
        return fig
    
    def run(self) -> None:
        """Run the dashboard server."""
        self.app.run_server(
            host=self.config['visualization']['dashboard']['host'],
            port=self.config['visualization']['dashboard']['port'],
            debug=self.config['visualization']['dashboard']['debug']
        )

def main():
    """Main function to run the dashboard."""
    dashboard = NuclearEnergyDashboard()
    dashboard.load_data()
    dashboard.run()

if __name__ == "__main__":
    main()