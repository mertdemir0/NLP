"""
Semantic analysis for nuclear energy content.
"""
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from sklearn.cluster import DBSCAN
from .base_analyzer import BaseAnalyzer

class SemanticAnalyzer(BaseAnalyzer):
    """Semantic analysis for nuclear energy content."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the semantic analyzer."""
        super().__init__(config_path)
        self.embedding_model = None
        
    def initialize_model(self) -> None:
        """Initialize the embedding model."""
        self.embedding_model = SentenceTransformer(
            self.config['analysis']['semantic']['embeddings_model']
        )
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Array of embeddings
        """
        if self.embedding_model is None:
            self.initialize_model()
            
        return self.embedding_model.encode(texts, show_progress_bar=True)
    
    def find_similar_articles(
        self,
        query_text: str,
        texts: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Find articles similar to a query text.
        
        Args:
            query_text: Text to compare against
            texts: List of texts to search through
            top_k: Number of similar articles to return
            
        Returns:
            List of similar articles with scores
        """
        if self.embedding_model is None:
            self.initialize_model()
            
        # Get embeddings
        query_embedding = self.embedding_model.encode(query_text)
        corpus_embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        
        # Calculate similarities
        similarities = util.pytorch_cos_sim(query_embedding, corpus_embeddings)[0]
        
        # Get top k similar articles
        top_results = []
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        for idx in top_indices:
            top_results.append({
                'text': texts[idx],
                'similarity': similarities[idx].item()
            })
            
        return top_results
    
    def cluster_articles(
        self,
        texts: List[str],
        min_samples: int = 5,
        eps: float = 0.3
    ) -> Tuple[List[int], List[Dict[str, Any]]]:
        """Cluster articles based on semantic similarity.
        
        Args:
            texts: List of texts to cluster
            min_samples: Minimum samples for DBSCAN
            eps: Maximum distance between samples for DBSCAN
            
        Returns:
            Tuple of (cluster labels, cluster information)
        """
        if self.embedding_model is None:
            self.initialize_model()
            
        # Get embeddings
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        
        # Perform clustering
        clustering = DBSCAN(eps=eps, min_samples=min_samples)
        labels = clustering.fit_predict(embeddings)
        
        # Analyze clusters
        clusters = []
        unique_labels = np.unique(labels)
        
        for label in unique_labels:
            if label != -1:  # Exclude noise points
                cluster_indices = np.where(labels == label)[0]
                cluster_texts = [texts[i] for i in cluster_indices]
                
                # Calculate cluster centroid
                centroid = embeddings[cluster_indices].mean(axis=0)
                
                # Find most representative article (closest to centroid)
                distances = np.linalg.norm(embeddings[cluster_indices] - centroid, axis=1)
                representative_idx = cluster_indices[np.argmin(distances)]
                
                clusters.append({
                    'cluster_id': int(label),
                    'size': len(cluster_indices),
                    'representative_text': texts[representative_idx],
                    'texts': cluster_texts
                })
        
        return labels.tolist(), clusters
    
    def analyze_technology_relationships(
        self,
        texts: List[str],
        technologies: List[List[str]]
    ) -> Dict[str, Dict[str, float]]:
        """Analyze semantic relationships between different technologies.
        
        Args:
            texts: List of texts to analyze
            technologies: List of technology categories for each text
            
        Returns:
            Dictionary of technology pair similarities
        """
        if self.embedding_model is None:
            self.initialize_model()
            
        # Group texts by technology
        tech_texts = {}
        for text, techs in zip(texts, technologies):
            for tech in techs:
                if tech not in tech_texts:
                    tech_texts[tech] = []
                tech_texts[tech].append(text)
        
        # Calculate average embedding for each technology
        tech_embeddings = {}
        for tech, tech_text_list in tech_texts.items():
            embeddings = self.embedding_model.encode(tech_text_list)
            tech_embeddings[tech] = embeddings.mean(axis=0)
        
        # Calculate similarities between technologies
        relationships = {}
        tech_list = list(tech_embeddings.keys())
        
        for i, tech1 in enumerate(tech_list):
            relationships[tech1] = {}
            for tech2 in tech_list[i+1:]:
                similarity = util.pytorch_cos_sim(
                    tech_embeddings[tech1],
                    tech_embeddings[tech2]
                ).item()
                relationships[tech1][tech2] = similarity
                
        return relationships

def main():
    """Main function to demonstrate usage."""
    analyzer = SemanticAnalyzer()
    analyzer.load_data()
    
    if analyzer.data is not None:
        # Example analysis
        texts = analyzer.data['content'].tolist()
        technologies = [analyzer.classify_technology(text) for text in texts]
        
        # Cluster articles
        labels, clusters = analyzer.cluster_articles(texts)
        
        # Analyze technology relationships
        tech_relationships = analyzer.analyze_technology_relationships(texts, technologies)
        
        # Find similar articles for a sample query
        if texts:
            similar_articles = analyzer.find_similar_articles(texts[0], texts[1:])
        else:
            similar_articles = []
        
        # Save results
        analyzer.save_results({
            'cluster_labels': labels,
            'clusters': clusters,
            'technology_relationships': tech_relationships,
            'similar_articles_example': similar_articles
        })

if __name__ == "__main__":
    main()