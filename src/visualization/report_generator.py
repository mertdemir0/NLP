"""
Report generator for nuclear energy content analysis.
"""
import os
from typing import Dict, Any, List
from datetime import datetime
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yaml
from jinja2 import Environment, FileSystemLoader

class ReportGenerator:
    """Generate reports from analysis results."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the report generator.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        self.env = Environment(loader=FileSystemLoader('templates'))
        self.results = {}
        
    @staticmethod
    def _load_config(config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def load_results(self, results_dir: str = "output") -> None:
        """Load analysis results."""
        # Load the most recent results for each analysis type
        for filename in os.listdir(results_dir):
            if filename.endswith('.yaml'):
                with open(os.path.join(results_dir, filename), 'r') as f:
                    results = yaml.safe_load(f)
                    analysis_type = filename.split('_')[0]
                    self.results[analysis_type] = results
    
    def generate_volume_analysis(self) -> Dict[str, Any]:
        """Generate content volume analysis visualizations."""
        if 'temporal' not in self.results:
            return {}
            
        # Create volume over time plot
        df = pd.DataFrame(self.results['temporal']['article_counts'])
        fig = px.line(
            df,
            x='date',
            y='count',
            title='Nuclear Energy Content Volume Over Time',
            template=self.config['visualization']['plots']['theme']
        )
        
        # Create technology distribution plot
        tech_df = pd.DataFrame(self.results['temporal']['technology_counts'])
        tech_fig = px.pie(
            tech_df,
            names='technology',
            values='count',
            title='Distribution by Nuclear Technology',
            template=self.config['visualization']['plots']['theme']
        )
        
        return {
            'volume_trend': fig.to_html(),
            'technology_dist': tech_fig.to_html(),
            'total_articles': df['count'].sum(),
            'peak_month': df.loc[df['count'].idxmax(), 'date'].strftime('%B %Y'),
            'technology_breakdown': tech_df.to_dict('records')
        }
    
    def generate_sentiment_analysis(self) -> Dict[str, Any]:
        """Generate sentiment analysis visualizations."""
        if 'sentiment' not in self.results:
            return {}
            
        # Create sentiment over time plot
        sentiment_df = pd.DataFrame(self.results['sentiment']['temporal_sentiment'])
        fig = px.line(
            sentiment_df,
            x='date',
            y='sentiment',
            title='Sentiment Trends Over Time',
            template=self.config['visualization']['plots']['theme']
        )
        
        # Create sentiment by technology plot
        tech_sentiment = pd.DataFrame(self.results['sentiment']['technology_sentiment'])
        tech_fig = px.box(
            tech_sentiment,
            x='technology',
            y='sentiment',
            title='Sentiment Distribution by Technology',
            template=self.config['visualization']['plots']['theme']
        )
        
        return {
            'sentiment_trend': fig.to_html(),
            'technology_sentiment': tech_fig.to_html(),
            'overall_sentiment': self.results['sentiment']['summary_statistics']['overall_sentiment'],
            'sentiment_by_tech': tech_sentiment.groupby('technology')['sentiment'].mean().to_dict()
        }
    
    def generate_topic_analysis(self) -> Dict[str, Any]:
        """Generate topic analysis visualizations."""
        if 'topic' not in self.results:
            return {}
            
        # Create topic evolution plot
        topic_df = pd.DataFrame(self.results['topic']['temporal_evolution'])
        fig = px.area(
            topic_df,
            title='Topic Evolution Over Time',
            template=self.config['visualization']['plots']['theme']
        )
        
        # Create topic distribution by technology plot
        tech_topics = pd.DataFrame(self.results['topic']['technology_distributions'])
        tech_fig = px.imshow(
            tech_topics,
            title='Topic Distribution by Technology',
            template=self.config['visualization']['plots']['theme']
        )
        
        return {
            'topic_evolution': fig.to_html(),
            'technology_topics': tech_fig.to_html(),
            'num_topics': self.results['topic']['summary']['num_topics'],
            'top_keywords': self.results['topic']['summary']['topic_keywords']
        }
    
    def generate_semantic_analysis(self) -> Dict[str, Any]:
        """Generate semantic analysis visualizations."""
        if 'semantic' not in self.results:
            return {}
            
        # Create technology relationship heatmap
        relationships = pd.DataFrame(self.results['semantic']['technology_relationships'])
        fig = px.imshow(
            relationships,
            title='Technology Relationship Matrix',
            template=self.config['visualization']['plots']['theme']
        )
        
        # Create cluster visualization
        clusters = pd.DataFrame(self.results['semantic']['clusters'])
        cluster_fig = px.scatter(
            clusters,
            x='x',
            y='y',
            color='cluster',
            title='Article Clusters',
            template=self.config['visualization']['plots']['theme']
        )
        
        return {
            'tech_relationships': fig.to_html(),
            'clusters': cluster_fig.to_html(),
            'num_clusters': len(clusters['cluster'].unique()),
            'cluster_sizes': clusters.groupby('cluster').size().to_dict()
        }
    
    def generate_html_report(self, output_path: str = "output/reports/report.html") -> None:
        """Generate HTML report combining all analyses.
        
        Args:
            output_path: Path to save the HTML report
        """
        template = self.env.get_template('report_template.html')
        
        report_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'volume_analysis': self.generate_volume_analysis(),
            'sentiment_analysis': self.generate_sentiment_analysis(),
            'topic_analysis': self.generate_topic_analysis(),
            'semantic_analysis': self.generate_semantic_analysis()
        }
        
        html_content = template.render(**report_data)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def generate_executive_summary(self, output_path: str = "output/reports/summary.md") -> None:
        """Generate executive summary in markdown format.
        
        Args:
            output_path: Path to save the markdown summary
        """
        template = self.env.get_template('summary_template.md')
        
        summary_data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'volume_analysis': self.generate_volume_analysis(),
            'sentiment_analysis': self.generate_sentiment_analysis(),
            'topic_analysis': self.generate_topic_analysis(),
            'semantic_analysis': self.generate_semantic_analysis()
        }
        
        markdown_content = template.render(**summary_data)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

def main():
    """Main function to demonstrate usage."""
    generator = ReportGenerator()
    generator.load_results()
    
    # Generate HTML report
    generator.generate_html_report()
    
    # Generate executive summary
    generator.generate_executive_summary()

if __name__ == "__main__":
    main()