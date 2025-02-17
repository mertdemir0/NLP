"""
Topic modeling for nuclear energy content.
"""
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from .base_analyzer import BaseAnalyzer

class TopicModeler(BaseAnalyzer):
    """Topic modeling for nuclear energy content."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the topic modeler."""
        super().__init__(config_path)
        self.topic_model = None
        self.embedding_model = None
        
    def initialize_models(self) -> None:
        """Initialize topic modeling and embedding models."""
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(
            self.config['analysis']['semantic']['embeddings_model']
        )
        
        # Initialize topic model with custom vectorizer
        vectorizer = CountVectorizer(
            stop_words="english",
            min_df=5,
            max_df=0.7
        )
        
        self.topic_model = BERTopic(
            embedding_model=self.embedding_model,
            vectorizer_model=vectorizer,
            nr_topics=self.config['analysis']['topic_modeling']['num_topics']
        )
    
    def analyze_topics(self, texts: List[str]) -> Tuple[List[int], np.ndarray]:
        """Analyze topics in texts.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            Tuple of (topic assignments, topic probabilities)
        """
        if self.topic_model is None:
            self.initialize_models()
            
        topics, probs = self.topic_model.fit_transform(texts)
        return topics, probs
    
    def analyze_topics_over_time(
        self,
        texts: List[str],
        dates: List[str],
        window: str = 'M'
    ) -> pd.DataFrame:
        """Analyze how topics evolve over time.
        
        Args:
            texts: List of texts to analyze
            dates: List of dates for each text
            window: Time window for aggregation ('D' for daily, 'M' for monthly, etc.)
            
        Returns:
            DataFrame with topic evolution over time
        """
        if self.topic_model is None:
            self.initialize_models()
            
        # Convert dates to datetime
        dates = pd.to_datetime(dates)
        
        # Fit the topic model
        topics, _ = self.topic_model.fit_transform(texts)
        
        # Create DataFrame with results
        df = pd.DataFrame({
            'date': dates,
            'topic': topics
        })
        
        # Group by time window and topic
        topic_evolution = df.groupby([
            pd.Grouper(key='date', freq=window),
            'topic'
        ]).size().unstack(fill_value=0)
        
        return topic_evolution
    
    def analyze_topics_by_technology(
        self,
        texts: List[str],
        technologies: List[List[str]]
    ) -> Dict[str, Dict[int, float]]:
        """Analyze topic distribution for each technology.
        
        Args:
            texts: List of texts to analyze
            technologies: List of technology categories for each text
            
        Returns:
            Dictionary mapping technologies to their topic distributions
        """
        if self.topic_model is None:
            self.initialize_models()
            
        # Fit the topic model
        topics, _ = self.topic_model.fit_transform(texts)
        
        # Create mapping of texts to their technologies
        tech_topics = {}
        for text_topics, techs in zip(topics, technologies):
            for tech in techs:
                if tech not in tech_topics:
                    tech_topics[tech] = []
                tech_topics[tech].append(text_topics)
        
        # Calculate topic distribution for each technology
        tech_distributions = {}
        for tech, topic_list in tech_topics.items():
            topic_counts = pd.Series(topic_list).value_counts()
            tech_distributions[tech] = (topic_counts / len(topic_list)).to_dict()
        
        return tech_distributions
    
    def get_topic_keywords(self, top_n: int = 10) -> Dict[int, List[Tuple[str, float]]]:
        """Get top keywords for each topic.
        
        Args:
            top_n: Number of top keywords to return per topic
            
        Returns:
            Dictionary mapping topic IDs to their top keywords and scores
        """
        if self.topic_model is None:
            raise ValueError("Topic model not initialized. Run analyze_topics first.")
            
        return {
            topic_id: keywords
            for topic_id, keywords in self.topic_model.get_topics().items()
            if topic_id != -1  # Exclude outlier topic
        }
    
    def get_topic_summary(self) -> Dict[str, Any]:
        """Get summary of topic modeling results.
        
        Returns:
            Dictionary with topic modeling summary
        """
        if self.topic_model is None:
            raise ValueError("Topic model not initialized. Run analyze_topics first.")
            
        topic_info = self.topic_model.get_topic_info()
        
        return {
            'num_topics': len(topic_info) - 1,  # Exclude outlier topic
            'topic_sizes': topic_info.set_index('Topic')['Count'].to_dict(),
            'topic_keywords': self.get_topic_keywords(),
            'coherence_score': self.topic_model.get_topic_coherence(),
        }

def main():
    """Main function to demonstrate usage."""
    modeler = TopicModeler()
    modeler.load_data()
    
    if modeler.data is not None:
        # Example analysis
        texts = modeler.data['content'].tolist()
        dates = modeler.data['date'].tolist()
        technologies = [modeler.classify_technology(text) for text in texts]
        
        # Analyze overall topics
        topics, probs = modeler.analyze_topics(texts)
        
        # Analyze temporal evolution
        topic_evolution = modeler.analyze_topics_over_time(texts, dates)
        
        # Analyze by technology
        tech_distributions = modeler.analyze_topics_by_technology(texts, technologies)
        
        # Get topic summary
        summary = modeler.get_topic_summary()
        
        # Save results
        modeler.save_results({
            'topic_assignments': topics.tolist(),
            'topic_probabilities': probs.tolist(),
            'temporal_evolution': topic_evolution.to_dict(),
            'technology_distributions': tech_distributions,
            'summary': summary
        })

if __name__ == "__main__":
    main()