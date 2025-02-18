"""News scraper module for collecting nuclear energy related articles."""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import json
import os
from newspaper import Article
from fake_useragent import UserAgent
from ..utils.logger import Logger
from ..database.models import ArticleDB
logger = Logger(__name__)

class NewsScraper:
    """Scraper for collecting nuclear energy related news articles."""
    
    def __init__(self, config: Dict):
        """Initialize the news scraper.
        
        Args:
            config: Configuration dictionary containing scraping settings
        """
        self.config = config
        self.ua = UserAgent()
        self.db = ArticleDB()
        self.logger = logging.getLogger(__name__)
        
        # Configure session with rotating user agents
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        })
    
    def _get_search_urls(self, query: str, days: int) -> List[str]:
        """Generate search URLs for different news sources.
        
        Args:
            query: Search query string
            days: Number of days to look back
            
        Returns:
            List[str]: List of URLs to scrape
        """
        urls = []
        date_str = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Bloomberg search URL
        bloomberg_url = (
            f"https://www.bloomberg.com/search?query={query}"
            f"&startTime={date_str}"
        )
        urls.append(bloomberg_url)
        
        # Add more news sources here as needed
        # Reuters, WSJ, etc.
        
        return urls
    
    def _extract_article_links(self, search_url: str) -> List[str]:
        """Extract article links from a search results page.
        
        Args:
            search_url: URL of the search results page
            
        Returns:
            List[str]: List of article URLs
        """
        try:
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            links = []
            
            # Extract links based on the source
            if 'bloomberg.com' in search_url:
                # Bloomberg specific extraction
                articles = soup.find_all('article')
                for article in articles:
                    link = article.find('a')
                    if link and 'href' in link.attrs:
                        url = link['href']
                        if not url.startswith('http'):
                            url = f"https://www.bloomberg.com{url}"
                        links.append(url)
            
            return links
            
        except Exception as e:
            self.logger.error(f"Error extracting links from {search_url}: {str(e)}")
            return []
    
    def _scrape_article(self, url: str) -> Optional[Dict]:
        """Scrape a single article.
        
        Args:
            url: URL of the article to scrape
            
        Returns:
            Dict or None: Article data if successful, None otherwise
        """
        try:
            # Check if article already exists
            existing = self.db.get_article_by_url(url)
            if existing:
                self.logger.info(f"Article already exists: {url}")
                return None
            
            # Download and parse article
            article = Article(url)
            article.download()
            article.parse()
            article.nlp()  # Extract keywords and summary
            
            # Create article dictionary
            article_data = {
                'title': article.title,
                'url': url,
                'content': article.text,
                'summary': article.summary,
                'published_date': article.publish_date.isoformat() if article.publish_date else None,
                'source': url.split('/')[2],  # Extract domain as source
                'author': ', '.join(article.authors) if article.authors else None,
                'keywords': article.keywords
            }
            
            return article_data
            
        except Exception as e:
            self.logger.error(f"Error scraping article {url}: {str(e)}")
            return None
    
    def run(self, query: str, days: int, output_dir: str) -> List[Dict]:
        """Run the scraper to collect articles.
        
        Args:
            query: Search query string
            days: Number of days to look back
            output_dir: Directory to save raw article data
            
        Returns:
            List[Dict]: List of scraped articles
        """
        self.logger.info(f"Starting scraper for query: {query} (last {days} days)")
        articles = []
        
        # Get search URLs
        search_urls = self._get_search_urls(query, days)
        
        # Extract article links
        article_links = []
        for url in search_urls:
            links = self._extract_article_links(url)
            article_links.extend(links)
        
        self.logger.info(f"Found {len(article_links)} articles to scrape")
        
        # Scrape articles
        for url in article_links:
            article_data = self._scrape_article(url)
            if article_data:
                # Save to database
                article_id = self.db.insert_article(article_data)
                if article_id:
                    self.logger.info(f"Saved article: {article_data['title']}")
                    articles.append(article_data)
        
        self.logger.info(f"Scraped {len(articles)} new articles")
        return articles
