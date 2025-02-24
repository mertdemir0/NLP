"""
Geographical entity extraction and analysis module for nuclear energy content.
"""

import spacy
from collections import Counter
from typing import Dict, List, Tuple, Optional
import pandas as pd
import folium
from pathlib import Path
import json
import logging
from .base_analyzer import BaseAnalyzer

logger = logging.getLogger(__name__)

class GeoAnalyzer(BaseAnalyzer):
    """Analyzes geographical entities in nuclear energy articles."""

    def __init__(self, model_name: str = "en_core_web_lg"):
        """
        Initialize the GeoAnalyzer.

        Args:
            model_name: Name of the spaCy model to use. Defaults to en_core_web_lg.
        """
        super().__init__()
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            logger.info(f"Downloading spaCy model: {model_name}")
            spacy.cli.download(model_name)
            self.nlp = spacy.load(model_name)
        
        # Load country coordinates data
        self.country_coords = self._load_country_coordinates()

    def _load_country_coordinates(self) -> Dict[str, Tuple[float, float]]:
        """
        Load country coordinates from a JSON file or return default coordinates.
        
        Returns:
            Dictionary mapping country names to (latitude, longitude) coordinates.
        """
        coords_file = Path(__file__).parent / "data" / "country_coordinates.json"
        try:
            with open(coords_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("Country coordinates file not found. Using default coordinates.")
            return {
                "United States": (37.0902, -95.7129),
                "China": (35.8617, 104.1954),
                "Russia": (61.5240, 105.3188),
                "France": (46.2276, 2.2137),
                # Add more default coordinates as needed
            }

    def extract_locations(self, text: str) -> List[Dict[str, str]]:
        """
        Extract geographical entities from text.

        Args:
            text: Input text to analyze.

        Returns:
            List of dictionaries containing location information.
        """
        doc = self.nlp(text)
        locations = []
        
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:
                locations.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char
                })
        
        return locations

    def analyze_articles(self, articles: List[Dict]) -> Dict:
        """
        Analyze geographical distribution in a collection of articles.

        Args:
            articles: List of article dictionaries with 'text' and 'date' fields.

        Returns:
            Dictionary containing geographical analysis results.
        """
        location_counts = Counter()
        temporal_locations = {}
        technology_locations = {}

        for article in articles:
            locations = self.extract_locations(article['text'])
            
            # Update overall counts
            for loc in locations:
                location_counts[loc['text']] += 1
            
            # Update temporal distribution
            date = pd.to_datetime(article['date']).strftime('%Y-%m')
            if date not in temporal_locations:
                temporal_locations[date] = Counter()
            temporal_locations[date].update(loc['text'] for loc in locations)
            
            # Update technology-specific distribution
            tech = self.classify_technology(article['text'])
            if tech:
                if tech not in technology_locations:
                    technology_locations[tech] = Counter()
                technology_locations[tech].update(loc['text'] for loc in locations)

        return {
            'location_counts': dict(location_counts),
            'temporal_locations': {k: dict(v) for k, v in temporal_locations.items()},
            'technology_locations': {k: dict(v) for k, v in technology_locations.items()}
        }

    def create_heatmap(self, location_data: Dict[str, int], 
                      output_path: Optional[str] = None) -> folium.Map:
        """
        Create a heatmap visualization of geographical mentions.

        Args:
            location_data: Dictionary mapping location names to mention counts.
            output_path: Optional path to save the map HTML file.

        Returns:
            Folium map object.
        """
        # Create base map centered on global view
        m = folium.Map(location=[20, 0], zoom_start=2)
        
        # Add markers for each location
        for loc_name, count in location_data.items():
            if loc_name in self.country_coords:
                lat, lon = self.country_coords[loc_name]
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=min(count * 2, 20),  # Scale marker size with count
                    popup=f"{loc_name}: {count} mentions",
                    color='red',
                    fill=True
                ).add_to(m)
        
        if output_path:
            m.save(output_path)
        
        return m

    def analyze_location_context(self, articles: List[Dict], 
                               location: str, 
                               window_size: int = 50) -> Dict:
        """
        Analyze the context around mentions of a specific location.

        Args:
            articles: List of article dictionaries.
            location: Location name to analyze.
            window_size: Number of characters before/after location to include.

        Returns:
            Dictionary containing context analysis results.
        """
        contexts = []
        sentiment_scores = []
        associated_techs = []

        for article in articles:
            text = article['text']
            doc = self.nlp(text)
            
            # Find all mentions of the location
            for ent in doc.ents:
                if ent.label_ in ["GPE", "LOC"] and ent.text.lower() == location.lower():
                    # Extract context
                    start = max(0, ent.start_char - window_size)
                    end = min(len(text), ent.end_char + window_size)
                    context = text[start:end]
                    contexts.append(context)
                    
                    # Analyze sentiment of context
                    context_doc = self.nlp(context)
                    sentiment = self._analyze_sentiment(context_doc)
                    sentiment_scores.append(sentiment)
                    
                    # Find associated technologies
                    tech = self.classify_technology(context)
                    if tech:
                        associated_techs.append(tech)

        return {
            'contexts': contexts,
            'sentiment': {
                'mean': sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0,
                'scores': sentiment_scores
            },
            'technologies': dict(Counter(associated_techs)),
            'mention_count': len(contexts)
        }

    def _analyze_sentiment(self, doc: spacy.tokens.Doc) -> float:
        """
        Simple rule-based sentiment analysis for location contexts.
        
        Args:
            doc: spaCy Doc object.
            
        Returns:
            Sentiment score between -1 and 1.
        """
        # Define sentiment lexicons
        positive_words = {
            'success', 'successful', 'positive', 'advance', 'progress', 'improve',
            'benefit', 'beneficial', 'advantage', 'cooperation', 'collaborate',
            'partnership', 'agreement', 'support', 'innovation', 'development',
            'sustainable', 'clean', 'efficient', 'safe', 'reliable'
        }
        
        negative_words = {
            'failure', 'failed', 'negative', 'problem', 'issue', 'concern',
            'risk', 'danger', 'threat', 'accident', 'incident', 'crisis',
            'conflict', 'dispute', 'controversy', 'opposition', 'protest',
            'waste', 'contamination', 'pollution', 'unsafe', 'unreliable'
        }
        
        # Count sentiment words
        positive_count = sum(1 for token in doc if token.text.lower() in positive_words)
        negative_count = sum(1 for token in doc if token.text.lower() in negative_words)
        
        # Calculate normalized sentiment score
        total_count = positive_count + negative_count
        if total_count == 0:
            return 0.0
        
        return (positive_count - negative_count) / total_count
