"""
Base class for nuclear energy content analysis.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd
import yaml
from transformers import pipeline
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create logs directory if it doesn't exist
log_dir = Path(os.getenv('LOG_DIR', 'logs'))
log_dir.mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BaseAnalyzer:
    """Base class for analyzing nuclear energy content."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the analyzer.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        self.data = None
        self.sentiment_analyzer = None
        self.topic_model = None
        self.embedding_model = None
        
    @staticmethod
    def _load_config(config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def load_data(self, data_dir: str = "data/raw") -> None:
        """Load articles from JSON files.
        
        Args:
            data_dir: Directory containing the article files
        """
        articles = []
        for filename in os.listdir(data_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(data_dir, filename), 'r') as f:
                        article = yaml.safe_load(f)
                        articles.append(article)
                except Exception as e:
                    logger.error(f"Error loading article from {filename}: {str(e)}")
        
        self.data = pd.DataFrame(articles)
        logger.info(f"Loaded {len(self.data)} articles")
    
    def initialize_models(self) -> None:
        """Initialize NLP models."""
        # Initialize sentiment analyzer
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model=self.config['analysis']['sentiment']['model']
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(
            self.config['analysis']['semantic']['embeddings_model']
        )
        
        # Initialize topic model
        self.topic_model = BERTopic(
            embedding_model=self.embedding_model,
            nr_topics=self.config['analysis']['topic_modeling']['num_topics']
        )
    
    def analyze_sentiment(self, texts: List[str]) -> List[Dict[str, float]]:
        """Analyze sentiment of texts.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of sentiment scores
        """
        if self.sentiment_analyzer is None:
            self.initialize_models()
            
        return self.sentiment_analyzer(texts)
    
    def analyze_topics(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze topics in texts.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            Dictionary containing topic model results
        """
        if self.topic_model is None:
            self.initialize_models()
            
        topics, probs = self.topic_model.fit_transform(texts)
        return {
            'topics': topics,
            'probabilities': probs,
            'topic_info': self.topic_model.get_topic_info()
        }
    
    def classify_technology(self, text: str) -> List[str]:
        """Classify text into nuclear technology categories.
        
        Args:
            text: Text to classify
            
        Returns:
            List of technology categories
        """
        categories = []
        for category in self.config['analysis']['technology_classification']['categories']:
            if any(keyword.lower() in text.lower() for keyword in category['keywords']):
                categories.append(category['name'])
        return categories
    
    def extract_geographical_info(self, text: str) -> Optional[str]:
        """Extract geographical information from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Extracted location or None
        """
        # TODO: Implement geographical entity extraction
        # This could be implemented using spaCy's NER or a dedicated geoparser
        pass
    
    def save_results(self, results: Dict[str, Any], output_dir: str = "output") -> None:
        """Save analysis results.
        
        Args:
            results: Analysis results
            output_dir: Directory to save results
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            with open(f"{output_dir}/analysis_results_{timestamp}.yaml", 'w') as f:
                yaml.dump(results, f, allow_unicode=True)
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")

def main():
    """Main function to demonstrate usage."""
    analyzer = BaseAnalyzer()
    analyzer.load_data()
    analyzer.initialize_models()
    
    if analyzer.data is not None:
        # Example analysis
        texts = analyzer.data['content'].tolist()
        sentiments = analyzer.analyze_sentiment(texts[:100])  # Analyze first 100 texts
        topics = analyzer.analyze_topics(texts[:100])
        
        results = {
            'sentiment_analysis': sentiments,
            'topic_analysis': topics
        }
        
        analyzer.save_results(results)

if __name__ == "__main__":
    main()
