"""
Bloomberg API client for fetching nuclear energy related articles and data.
"""

import logging
from typing import Dict, List, Optional
import datetime
import blpapi

logger = logging.getLogger(__name__)

class BloombergClient:
    """Client for interacting with Bloomberg API to fetch news and data."""
    
    def __init__(self, config: Dict):
        """
        Initialize Bloomberg API client.
        
        Args:
            config: Configuration dictionary containing Bloomberg API settings
        """
        self.config = config
        self.session_options = blpapi.SessionOptions()
        self.session_options.setServerHost(config.get('bloomberg_host', 'localhost'))
        self.session_options.setServerPort(config.get('bloomberg_port', 8194))
        
        # Set authentication options if provided
        if 'bloomberg_auth' in config:
            auth_options = blpapi.AuthOptions()
            auth_options.setUserName(config['bloomberg_auth']['username'])
            auth_options.setPassword(config['bloomberg_auth']['password'])
            self.session_options.setAuthenticationOptions(auth_options)
        
        self.session = None
    
    def connect(self) -> bool:
        """
        Establish connection to Bloomberg API.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.session = blpapi.Session(self.session_options)
            if not self.session.start():
                logger.error("Failed to start Bloomberg API session")
                return False
            
            if not self.session.openService("//blp/mktdata"):
                logger.error("Failed to open market data service")
                return False
            
            if not self.session.openService("//blp/news"):
                logger.error("Failed to open news service")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to Bloomberg API: {str(e)}")
            return False
    
    def disconnect(self):
        """Close the Bloomberg API session."""
        if self.session:
            self.session.stop()
            self.session = None
    
    def fetch_news_articles(
        self,
        topics: List[str],
        start_date: datetime.datetime,
        end_date: Optional[datetime.datetime] = None,
        max_articles: int = 1000
    ) -> List[Dict]:
        """
        Fetch news articles related to nuclear energy.
        
        Args:
            topics: List of topics/keywords to search for
            start_date: Start date for article search
            end_date: End date for article search (defaults to current time)
            max_articles: Maximum number of articles to fetch
            
        Returns:
            List of dictionaries containing article data
        """
        if not self.session:
            if not self.connect():
                return []
        
        try:
            # Create news request
            news_service = self.session.getService("//blp/news")
            request = news_service.createRequest("NewsSearchRequest")
            
            # Set search parameters
            request.set("searchString", " OR ".join(topics))
            request.set("dateFrom", start_date.strftime("%Y-%m-%d"))
            if end_date:
                request.set("dateTo", end_date.strftime("%Y-%m-%d"))
            request.set("maxResults", max_articles)
            
            # Send request
            correlation_id = blpapi.CorrelationId("NewsSearch")
            self.session.sendRequest(request, correlationId=correlation_id)
            
            # Process response
            articles = []
            done = False
            while not done:
                event = self.session.nextEvent(500)
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    done = True
                
                for msg in event:
                    if msg.correlationIds()[0].value() == "NewsSearch":
                        articles.extend(self._process_news_message(msg))
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching news articles: {str(e)}")
            return []
        
    def _process_news_message(self, msg: blpapi.Message) -> List[Dict]:
        """
        Process a news message from Bloomberg API.
        
        Args:
            msg: Bloomberg API message
            
        Returns:
            List of dictionaries containing article data
        """
        articles = []
        
        try:
            if msg.hasElement("totalResults"):
                total_results = msg.getElement("totalResults").getValueAsInteger()
                logger.info(f"Total results found: {total_results}")
            
            if msg.hasElement("articles"):
                articles_element = msg.getElement("articles")
                for i in range(articles_element.numValues()):
                    article = articles_element.getValueAsElement(i)
                    
                    article_data = {
                        'headline': article.getElementAsString("headline"),
                        'body': article.getElementAsString("body"),
                        'date': article.getElementAsDatetime("publishedAt"),
                        'source': article.getElementAsString("source"),
                        'uri': article.getElementAsString("uri"),
                        'metadata': {}
                    }
                    
                    # Extract additional metadata if available
                    if article.hasElement("metadata"):
                        metadata = article.getElement("metadata")
                        for j in range(metadata.numElements()):
                            field = metadata.getElement(j)
                            article_data['metadata'][field.name()] = field.getValueAsString()
                    
                    articles.append(article_data)
        
        except Exception as e:
            logger.error(f"Error processing news message: {str(e)}")
        
        return articles
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
