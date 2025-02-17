"""
Bloomberg API client for fetching nuclear energy related articles.
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import aiohttp
import yaml
from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'logs/app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BloombergClient:
    """Client for interacting with Bloomberg's API."""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize the Bloomberg API client.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        self.api_key = os.getenv('BLOOMBERG_API_KEY')
        self.api_secret = os.getenv('BLOOMBERG_API_SECRET')
        self.api_token = os.getenv('BLOOMBERG_API_TOKEN')
        
        if not all([self.api_key, self.api_secret, self.api_token]):
            raise ValueError("Bloomberg API credentials not found in environment variables")
        
        self.base_url = self.config['bloomberg']['api']['base_url']
        self.rate_limit = self.config['bloomberg']['api']['rate_limit']
        self.semaphore = asyncio.Semaphore(self.rate_limit)

    @staticmethod
    def _load_config(config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_request(self, session: aiohttp.ClientSession, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make an API request with retry logic."""
        async with self.semaphore:
            async with session.get(url, params=params, headers=self._get_headers()) as response:
                response.raise_for_status()
                return await response.json()

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    async def fetch_articles(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        topics: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch articles from Bloomberg API.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            topics: List of topics to search for
            
        Returns:
            List of article data
        """
        start_date = start_date or self.config['bloomberg']['start_date']
        end_date = end_date or self.config['bloomberg']['end_date']
        topics = topics or self.config['bloomberg']['topics']
        
        articles = []
        async with aiohttp.ClientSession() as session:
            for topic in topics:
                logger.info(f"Fetching articles for topic: {topic}")
                params = {
                    'query': topic,
                    'dateRange': {
                        'startDate': start_date,
                        'endDate': end_date
                    },
                    'page': 1,
                    'perPage': self.config['bloomberg']['api']['max_results_per_page']
                }
                
                while True:
                    try:
                        response = await self._make_request(
                            session,
                            f"{self.base_url}{self.config['bloomberg']['api']['articles_endpoint']}",
                            params
                        )
                        
                        if not response.get('articles'):
                            break
                            
                        articles.extend(response['articles'])
                        
                        if len(response['articles']) < params['perPage']:
                            break
                            
                        params['page'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error fetching articles for topic {topic}: {str(e)}")
                        break
        
        return self._deduplicate_articles(articles)

    @staticmethod
    def _deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate articles based on article ID."""
        seen_ids = set()
        unique_articles = []
        
        for article in articles:
            if article['id'] not in seen_ids:
                seen_ids.add(article['id'])
                unique_articles.append(article)
        
        return unique_articles

    async def save_articles(self, articles: List[Dict[str, Any]], output_dir: str = "data/raw") -> None:
        """Save articles to JSON files.
        
        Args:
            articles: List of article data
            output_dir: Directory to save the articles
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, article in enumerate(articles):
            filename = f"{output_dir}/article_{timestamp}_{i}.json"
            try:
                with open(filename, 'w') as f:
                    yaml.dump(article, f, allow_unicode=True)
            except Exception as e:
                logger.error(f"Error saving article to {filename}: {str(e)}")

async def main():
    """Main function to demonstrate usage."""
    client = BloombergClient()
    articles = await client.fetch_articles()
    await client.save_articles(articles)

if __name__ == "__main__":
    asyncio.run(main())
