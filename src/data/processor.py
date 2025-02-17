"""
Data processing pipeline for nuclear sentiment analysis.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Generator
import logging
from elasticsearch import AsyncElasticsearch
import redis
from newspaper import Article
from trafilatura import extract
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class ProcessedArticle:
    id: str
    title: str
    content: str
    source: str
    url: str
    published_date: datetime
    language: str
    metadata: Dict

class DataProcessor:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Initialize Elasticsearch client
        self.es = AsyncElasticsearch([
            self.config.get("elasticsearch_url", "http://localhost:9200")
        ])
        
        # Initialize Redis client
        self.redis = redis.Redis(
            host=self.config.get("redis_host", "localhost"),
            port=self.config.get("redis_port", 6379),
            decode_responses=True
        )
        
        self.batch_size = self.config.get("batch_size", 1000)
    
    async def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        try:
            # Remove HTML
            soup = BeautifulSoup(text, "lxml")
            text = soup.get_text()
            
            # Normalize whitespace
            text = " ".join(text.split())
            
            # Basic cleaning
            text = text.replace("\n", " ")
            text = text.replace("\t", " ")
            
            return text.strip()
        
        except Exception as e:
            logger.error(f"Text cleaning failed: {str(e)}")
            return text
    
    async def extract_article_content(self, url: str) -> Optional[Article]:
        """Extract article content using newspaper3k and trafilatura."""
        try:
            # Try newspaper3k first
            article = Article(url)
            article.download()
            article.parse()
            
            if not article.text:
                # Fallback to trafilatura
                content = extract(article.html)
                if content:
                    article.text = content
            
            if article.text:
                article.text = await self.clean_text(article.text)
                return article
            
            return None
        
        except Exception as e:
            logger.error(f"Article extraction failed for {url}: {str(e)}")
            return None
    
    async def process_article(self, raw_article: Dict) -> Optional[ProcessedArticle]:
        """Process a single article."""
        try:
            # Extract content
            article = await self.extract_article_content(raw_article["url"])
            if not article:
                return None
            
            # Create processed article
            processed = ProcessedArticle(
                id=raw_article["id"],
                title=article.title,
                content=article.text,
                source=raw_article["source"],
                url=raw_article["url"],
                published_date=article.publish_date or datetime.now(),
                language=article.meta_lang or "en",
                metadata={
                    "authors": article.authors,
                    "keywords": article.keywords,
                    "summary": article.summary,
                    "processed_date": datetime.now().isoformat()
                }
            )
            
            # Cache in Redis
            cache_key = f"article:{processed.id}"
            self.redis.setex(
                cache_key,
                self.config.get("cache_ttl", 86400),
                json.dumps(processed.__dict__)
            )
            
            return processed
        
        except Exception as e:
            logger.error(f"Article processing failed: {str(e)}")
            return None
    
    async def store_processed_article(self, article: ProcessedArticle):
        """Store processed article in Elasticsearch."""
        try:
            await self.es.index(
                index="nuclear_news_processed",
                id=article.id,
                document=article.__dict__,
                refresh=True
            )
        except Exception as e:
            logger.error(f"Failed to store article {article.id}: {str(e)}")
    
    async def get_new_data_count(self) -> int:
        """Get count of new unprocessed articles."""
        try:
            result = await self.es.count(
                index="nuclear_news_raw",
                body={
                    "query": {
                        "bool": {
                            "must_not": {
                                "exists": {
                                    "field": "processed_date"
                                }
                            }
                        }
                    }
                }
            )
            return result["count"]
        except Exception as e:
            logger.error(f"Failed to get new data count: {str(e)}")
            return 0
    
    async def get_new_data(self) -> Generator:
        """Get new unprocessed articles in batches."""
        try:
            # Scroll through unprocessed articles
            resp = await self.es.search(
                index="nuclear_news_raw",
                body={
                    "query": {
                        "bool": {
                            "must_not": {
                                "exists": {
                                    "field": "processed_date"
                                }
                            }
                        }
                    }
                },
                scroll="5m",
                size=self.batch_size
            )
            
            scroll_id = resp["_scroll_id"]
            
            while True:
                batch = []
                
                # Process current batch
                for hit in resp["hits"]["hits"]:
                    article = await self.process_article(hit["_source"])
                    if article:
                        batch.append(article)
                        await self.store_processed_article(article)
                
                if batch:
                    yield batch
                
                # Get next batch
                resp = await self.es.scroll(
                    scroll_id=scroll_id,
                    scroll="5m"
                )
                
                # Stop if no more results
                if not resp["hits"]["hits"]:
                    break
            
            # Clear scroll
            await self.es.clear_scroll(scroll_id=scroll_id)
        
        except Exception as e:
            logger.error(f"Failed to get new data: {str(e)}")
            yield []
    
    async def get_eval_data(self) -> List[Dict]:
        """Get evaluation dataset."""
        try:
            result = await self.es.search(
                index="nuclear_news_processed",
                body={
                    "query": {
                        "range": {
                            "processed_date": {
                                "gte": "now-7d/d"
                            }
                        }
                    }
                },
                size=self.config.get("eval_size", 1000)
            )
            
            return [hit["_source"] for hit in result["hits"]["hits"]]
        
        except Exception as e:
            logger.error(f"Failed to get eval data: {str(e)}")
            return []
    
    async def get_last_training_time(self) -> Optional[datetime]:
        """Get timestamp of last model training."""
        try:
            result = await self.es.search(
                index="model_metrics",
                body={
                    "query": {
                        "match_all": {}
                    },
                    "sort": [
                        {
                            "training_date": {
                                "order": "desc"
                            }
                        }
                    ]
                },
                size=1
            )
            
            if result["hits"]["hits"]:
                return datetime.fromisoformat(
                    result["hits"]["hits"][0]["_source"]["training_date"]
                )
            return None
        
        except Exception as e:
            logger.error(f"Failed to get last training time: {str(e)}")
            return None
