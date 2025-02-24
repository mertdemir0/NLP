"""
Visualization module for creating interactive dashboards and reports.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Optional
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import numpy as np
from pathlib import Path

class VisualizationManager:
    """Creates and manages visualizations for analysis results."""
    
    def __init__(self, output_dir: str = "reports"):
        """
        Initialize the visualization manager.
        
        Args:
            output_dir: Directory to save visualization outputs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def create_temporal_plot(self, data: pd.DataFrame, 
                           time_col: str = 'date',
                           value_col: str = 'value',
                           title: str = 'Temporal Analysis') -> go.Figure:
        """Create temporal trend visualization."""
        fig = go.Figure()
        
        # Add time series line
        fig.add_trace(go.Scatter(
            x=data[time_col],
            y=data[value_col],
            mode='lines+markers',
            name='Value'
        ))
        
        # Add trend line
        z = np.polyfit(range(len(data)), data[value_col], 1)
        p = np.poly1d(z)
        fig.add_trace(go.Scatter(
            x=data[time_col],
            y=p(range(len(data))),
            mode='lines',
            name='Trend',
            line=dict(dash='dash')
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Value",
            template="plotly_white"
        )
        
        return fig
    
    def create_sentiment_heatmap(self, sentiment_data: pd.DataFrame,
                               x_col: str,
                               y_col: str,
                               value_col: str,
                               title: str = 'Sentiment Analysis') -> go.Figure:
        """Create sentiment heatmap visualization."""
        pivot_table = sentiment_data.pivot_table(
            values=value_col,
            index=y_col,
            columns=x_col,
            aggfunc='mean'
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_table.values,
            x=pivot_table.columns,
            y=pivot_table.index,
            colorscale='RdBu',
            zmid=0
        ))
        
        fig.update_layout(
            title=title,
            template="plotly_white"
        )
        
        return fig
    
    def create_technology_comparison(self, tech_data: pd.DataFrame,
                                   tech_col: str = 'technology',
                                   value_col: str = 'count') -> go.Figure:
        """Create technology comparison visualization."""
        fig = go.Figure(data=[
            go.Bar(
                x=tech_data[tech_col],
                y=tech_data[value_col],
                marker_color='lightblue'
            )
        ])
        
        fig.update_layout(
            title='Technology Distribution',
            xaxis_title="Technology",
            yaxis_title="Count",
            template="plotly_white"
        )
        
        return fig
    
    def create_dashboard(self, temporal_data: pd.DataFrame,
                        sentiment_data: pd.DataFrame,
                        tech_data: pd.DataFrame) -> dash.Dash:
        """Create an interactive dashboard."""
        app = dash.Dash(__name__)
        
        app.layout = html.Div([
            html.H1("Nuclear Energy Content Analysis Dashboard"),
            
            html.Div([
                html.H2("Temporal Analysis"),
                dcc.Graph(
                    id='temporal-plot',
                    figure=self.create_temporal_plot(temporal_data)
                )
            ]),
            
            html.Div([
                html.H2("Sentiment Analysis"),
                dcc.Graph(
                    id='sentiment-heatmap',
                    figure=self.create_sentiment_heatmap(
                        sentiment_data,
                        'date',
                        'technology',
                        'sentiment'
                    )
                )
            ]),
            
            html.Div([
                html.H2("Technology Distribution"),
                dcc.Graph(
                    id='tech-comparison',
                    figure=self.create_technology_comparison(tech_data)
                )
            ])
        ])
        
        return app
    
    def save_visualization(self, fig: go.Figure, filename: str):
        """Save visualization to file."""
        output_path = self.output_dir / filename
        fig.write_html(str(output_path))
