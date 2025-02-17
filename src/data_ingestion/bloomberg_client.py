"""
Bloomberg API client for fetching nuclear energy related articles and data.
"""

import logging
from typing import Dict, List, Optional, Union
import datetime
import blpapi
import pandas as pd

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
        self._market_data_subscriptions = {}
    
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
            
            services = [
                "//blp/mktdata",
                "//blp/news",
                "//blp/refdata",
                "//blp/apifields"
            ]
            
            for service in services:
                if not self.session.openService(service):
                    logger.error(f"Failed to open {service} service")
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
        max_articles: int = 1000,
        languages: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Fetch news articles related to nuclear energy.
        
        Args:
            topics: List of topics/keywords to search for
            start_date: Start date for article search
            end_date: End date for article search (defaults to current time)
            max_articles: Maximum number of articles to fetch
            languages: List of language codes to filter articles
            
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
            
            if languages:
                request.set("languageOverride", languages)
            
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
    
    def fetch_company_data(
        self,
        companies: List[str],
        fields: List[str],
        start_date: Optional[datetime.datetime] = None,
        end_date: Optional[datetime.datetime] = None
    ) -> pd.DataFrame:
        """
        Fetch historical data for nuclear energy companies.
        
        Args:
            companies: List of company tickers
            fields: List of Bloomberg fields to retrieve
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            DataFrame containing company data
        """
        if not self.session:
            if not self.connect():
                return pd.DataFrame()
        
        try:
            refdata_service = self.session.getService("//blp/refdata")
            request = refdata_service.createRequest("HistoricalDataRequest")
            
            # Set securities and fields
            for company in companies:
                request.getElement("securities").appendValue(company)
            for field in fields:
                request.getElement("fields").appendValue(field)
            
            # Set date range
            if start_date:
                request.set("startDate", start_date.strftime("%Y%m%d"))
            if end_date:
                request.set("endDate", end_date.strftime("%Y%m%d"))
            
            # Send request
            self.session.sendRequest(request)
            
            # Process response
            data = []
            done = False
            while not done:
                event = self.session.nextEvent(500)
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    done = True
                
                for msg in event:
                    security_data = msg.getElement("securityData")
                    ticker = security_data.getElementAsString("security")
                    field_data = security_data.getElement("fieldData")
                    
                    for i in range(field_data.numValues()):
                        field_values = field_data.getValueAsElement(i)
                        row_data = {'ticker': ticker}
                        
                        for field in fields:
                            if field_values.hasElement(field):
                                row_data[field] = field_values.getElementAsFloat(field)
                            else:
                                row_data[field] = None
                        
                        if field_values.hasElement("date"):
                            row_data['date'] = field_values.getElementAsDatetime("date")
                        
                        data.append(row_data)
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Error fetching company data: {str(e)}")
            return pd.DataFrame()
    
    def subscribe_to_market_data(
        self,
        securities: List[str],
        fields: List[str],
        callback: callable
    ) -> bool:
        """
        Subscribe to real-time market data updates.
        
        Args:
            securities: List of securities to subscribe to
            fields: List of fields to monitor
            callback: Callback function for handling updates
            
        Returns:
            bool: True if subscription successful
        """
        if not self.session:
            if not self.connect():
                return False
        
        try:
            # Create subscription list
            subscriptions = blpapi.SubscriptionList()
            
            for security in securities:
                correlation_id = blpapi.CorrelationId(security)
                subscriptions.add(
                    security,
                    fields,
                    correlationId=correlation_id
                )
                self._market_data_subscriptions[security] = callback
            
            self.session.subscribe(subscriptions)
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing to market data: {str(e)}")
            return False
    
    def get_field_info(self, field: str) -> Dict:
        """
        Get information about a Bloomberg field.
        
        Args:
            field: Bloomberg field to get info for
            
        Returns:
            Dictionary containing field information
        """
        if not self.session:
            if not self.connect():
                return {}
        
        try:
            apifields_service = self.session.getService("//blp/apifields")
            request = apifields_service.createRequest("FieldInfoRequest")
            request.set("id", field)
            
            # Send request
            self.session.sendRequest(request)
            
            # Process response
            field_info = {}
            done = False
            while not done:
                event = self.session.nextEvent(500)
                
                if event.eventType() == blpapi.Event.RESPONSE:
                    done = True
                
                for msg in event:
                    if msg.hasElement("fieldData"):
                        field_data = msg.getElement("fieldData")
                        field_info = {
                            'id': field_data.getElementAsString("id"),
                            'mnemonic': field_data.getElementAsString("mnemonic"),
                            'description': field_data.getElementAsString("description"),
                            'documentation': field_data.getElementAsString("documentation"),
                            'datatype': field_data.getElementAsString("datatype")
                        }
            
            return field_info
            
        except Exception as e:
            logger.error(f"Error getting field info: {str(e)}")
            return {}
    
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
