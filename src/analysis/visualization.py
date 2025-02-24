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
        fig = px.line(data, 
                     x=time_col, 
                     y=value_col, 
                     color='source',
                     title=title)
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Number of Articles",
            template="plotly_white",
            hovermode='x unified'
        )
        
        return fig
    
    def create_sentiment_heatmap(self, sentiment_data: pd.DataFrame,
                               x_col: str = 'date',
                               y_col: str = 'source',
                               value_col: str = 'sentiment',
                               title: str = 'Sentiment Analysis') -> go.Figure:
        """Create sentiment heatmap visualization."""
        # Aggregate sentiment scores by date and source
        pivot_table = sentiment_data.pivot_table(
            values=value_col,
            index=y_col,
            columns=x_col,
            aggfunc='mean',
            fill_value=0
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_table.values,
            x=pivot_table.columns,
            y=pivot_table.index,
            colorscale='RdBu',
            zmid=0,
            text=np.round(pivot_table.values, 2),
            texttemplate='%{text}',
            textfont={"size": 10},
            hoverongaps=False
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Source",
            template="plotly_white"
        )
        
        return fig
    
    def create_technology_comparison(self, tech_data: pd.DataFrame,
                                   tech_col: str = 'technology',
                                   value_col: str = 'count',
                                   source_col: str = 'source',
                                   title: str = 'Technology Distribution') -> go.Figure:
        """Create technology comparison visualization."""
        fig = px.bar(tech_data, 
                    x=tech_col, 
                    y=value_col,
                    color=source_col,
                    barmode='group',
                    title=title)
        
        fig.update_layout(
            xaxis_title="Technology",
            yaxis_title="Count",
            template="plotly_white",
            showlegend=True,
            legend_title="Source",
            xaxis_tickangle=-45
        )
        
        return fig
    
    def create_dashboard(self,
                        temporal_fig: go.Figure,
                        sentiment_fig: go.Figure,
                        tech_fig: go.Figure,
                        title: str = "Analysis Dashboard") -> dash.Dash:
        """Create an interactive dashboard."""
        app = dash.Dash(__name__)
        
        app.layout = html.Div([
            html.H1(title, style={'textAlign': 'center', 'marginBottom': 30}),
            
            html.Div([
                html.H2("Content Volume Over Time", style={'textAlign': 'center'}),
                dcc.Graph(figure=temporal_fig)
            ], style={'marginBottom': 40}),
            
            html.Div([
                html.H2("Sentiment Analysis", style={'textAlign': 'center'}),
                dcc.Graph(figure=sentiment_fig)
            ], style={'marginBottom': 40}),
            
            html.Div([
                html.H2("Technology Distribution", style={'textAlign': 'center'}),
                dcc.Graph(figure=tech_fig)
            ])
        ], style={
            'padding': '20px',
            'maxWidth': '1200px',
            'margin': 'auto',
            'fontFamily': 'Arial, sans-serif'
        })
        
        return app
    
    def save_visualization(self, fig: go.Figure, filename: str):
        """Save visualization to file."""
        output_path = self.output_dir / filename
        fig.write_html(str(output_path))
