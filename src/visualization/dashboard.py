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
import json
from pathlib import Path

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
        self.country_coords = self._load_country_coordinates()
        self.setup_layout()
        self._setup_callbacks()
        
    @staticmethod
    def _load_config(config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_country_coordinates(self) -> Dict[str, List[float]]:
        """Load country coordinates for geographical visualization."""
        coords_file = Path(__file__).parent.parent / "config" / "country_coordinates.json"
        with open(coords_file, 'r') as f:
            return json.load(f)
    
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
                html.H3("Geographical Analysis"),
                html.Div([
                    html.Div([
                        html.H4("Location Mentions Over Time"),
                        dcc.Graph(id='geo-temporal-chart')
                    ], className='six columns'),
                    html.Div([
                        html.H4("Location Distribution"),
                        dcc.Graph(id='geo-dist-chart')
                    ], className='six columns'),
                ], className='row'),
                html.Div([
                    html.H4("Geographical Heatmap"),
                    dcc.Graph(id='geo-heatmap')
                ]),
                html.Div([
                    html.H4("Location Context Analysis"),
                    dcc.Dropdown(
                        id='location-selector',
                        placeholder='Select a location to analyze...'
                    ),
                    html.Div(id='location-context')
                ])
            ])
        ])
    
    def _setup_callbacks(self):
        """Set up dashboard callbacks."""
        @self.app.callback(
            [Output('geo-temporal-chart', 'figure'),
             Output('geo-dist-chart', 'figure'),
             Output('geo-heatmap', 'figure'),
             Output('location-selector', 'options')],
            [Input('date-range', 'start_date'),
             Input('date-range', 'end_date'),
             Input('technology-filter', 'value')]
        )
        def update_geo_charts(start_date, end_date, selected_techs):
            # Filter data based on date range and technologies
            filtered_data = self._filter_data(start_date, end_date, selected_techs)
            
            # Create temporal chart
            temporal_fig = self.create_geo_temporal_chart(filtered_data)
            
            # Create distribution chart
            dist_fig = self.create_geo_distribution_chart(filtered_data)
            
            # Create heatmap
            heatmap_fig = self.create_geo_heatmap(filtered_data)
            
            # Update location selector options
            location_options = [
                {'label': loc, 'value': loc}
                for loc in filtered_data.get('location_counts', {}).keys()
            ]
            
            return temporal_fig, dist_fig, heatmap_fig, location_options

        @self.app.callback(
            Output('location-context', 'children'),
            [Input('location-selector', 'value')]
        )
        def update_location_context(selected_location):
            if not selected_location:
                return html.Div("Select a location to view its analysis")
            
            context_data = self.data.get('location_contexts', {}).get(selected_location, {})
            
            return html.Div([
                html.P(f"Total Mentions: {context_data.get('mention_count', 0)}"),
                html.P(f"Average Sentiment: {context_data.get('sentiment', {}).get('mean', 0):.2f}"),
                html.H5("Associated Technologies:"),
                html.Ul([
                    html.Li(f"{tech}: {count}")
                    for tech, count in context_data.get('technologies', {}).items()
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
    
    def create_geo_temporal_chart(self, data: Dict) -> go.Figure:
        """Create temporal chart of location mentions."""
        df = pd.DataFrame([
            {'date': date, 'location': loc, 'count': count}
            for date, locs in data.get('temporal_locations', {}).items()
            for loc, count in locs.items()
        ])
        
        fig = px.line(
            df,
            x='date',
            y='count',
            color='location',
            title='Location Mentions Over Time',
            template=self.config['visualization']['plots']['theme']
        )
        return fig
    
    def create_geo_distribution_chart(self, data: Dict) -> go.Figure:
        """Create geographical distribution chart."""
        df = pd.DataFrame([
            {'location': loc, 'count': count}
            for loc, count in data.get('location_counts', {}).items()
        ])
        
        fig = px.bar(
            df,
            x='location',
            y='count',
            title='Distribution of Location Mentions',
            template=self.config['visualization']['plots']['theme']
        )
        fig.update_layout(xaxis_tickangle=-45)
        return fig
    
    def create_geo_heatmap(self, data: Dict) -> go.Figure:
        """Create geographical heatmap."""
        locations = []
        counts = []
        texts = []
        
        for loc, count in data.get('location_counts', {}).items():
            if loc in self.country_coords:
                locations.append(loc)
                counts.append(count)
                texts.append(f"{loc}: {count} mentions")
        
        lats = [self.country_coords[loc][0] for loc in locations]
        lons = [self.country_coords[loc][1] for loc in locations]
        
        fig = go.Figure(data=go.Scattergeo(
            lon=lons,
            lat=lats,
            text=texts,
            mode='markers',
            marker=dict(
                size=[min(count * 2, 20) for count in counts],
                color=counts,
                colorscale='Viridis',
                showscale=True,
                colorbar_title="Mention Count"
            )
        ))
        
        fig.update_layout(
            title='Geographical Distribution of Nuclear Energy Coverage',
            geo=dict(
                showland=True,
                showcountries=True,
                showocean=True,
                countrywidth=0.5,
                landcolor='rgb(243, 243, 243)',
                oceancolor='rgb(204, 229, 255)',
                projection_scale=1.2
            ),
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