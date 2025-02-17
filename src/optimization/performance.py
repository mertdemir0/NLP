"""
Performance optimization for nuclear sentiment analysis.
"""

import asyncio
from typing import Dict, List, Optional
import logging
import torch
from torch.cuda.amp import autocast, GradScaler
import redis
from elasticsearch import AsyncElasticsearch
import dask.dataframe as dd
import vaex
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    throughput: float  # articles per second
    latency: float    # seconds per article
    memory_usage: float  # MB
    gpu_usage: float    # percentage
    cache_hit_rate: float  # percentage

class PerformanceOptimizer:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Initialize Redis client
        self.redis = redis.Redis(
            host=self.config.get("redis_host", "localhost"),
            port=self.config.get("redis_port", 6379),
            decode_responses=True
        )
        
        # Initialize Elasticsearch client
        self.es = AsyncElasticsearch([
            self.config.get("elasticsearch_url", "http://localhost:9200")
        ])
        
        # Initialize thread pool
        self.executor = ThreadPoolExecutor(
            max_workers=self.config.get("max_workers", 4)
        )
        
        # Initialize gradient scaler for mixed precision
        self.scaler = GradScaler()
        
        # Cache settings
        self.cache_ttl = self.config.get("cache_ttl", 3600)
        self.batch_size = self.config.get("batch_size", 64)
    
    async def optimize_batch_processing(
        self,
        data: List[Dict]
    ) -> List[Dict]:
        """Optimize batch processing using Dask."""
        try:
            # Convert to Dask DataFrame
            df = dd.from_pandas(
                pd.DataFrame(data),
                npartitions=self.config.get("num_partitions", 4)
            )
            
            # Parallel processing
            results = await self._process_in_parallel(df)
            
            return results.compute().to_dict('records')
        
        except Exception as e:
            logger.error(f"Batch processing optimization failed: {str(e)}")
            return data
    
    async def optimize_model_inference(
        self,
        model: torch.nn.Module,
        inputs: Dict[str, torch.Tensor]
    ) -> Dict[str, torch.Tensor]:
        """Optimize model inference with mixed precision."""
        try:
            with autocast():
                outputs = model(**inputs)
            
            return outputs
        
        except Exception as e:
            logger.error(f"Model inference optimization failed: {str(e)}")
            return model(**inputs)
    
    async def optimize_training(
        self,
        model: torch.nn.Module,
        optimizer: torch.optim.Optimizer,
        loss_fn: callable,
        inputs: Dict[str, torch.Tensor],
        labels: torch.Tensor
    ) -> float:
        """Optimize training with mixed precision."""
        try:
            # Forward pass with mixed precision
            with autocast():
                outputs = model(**inputs)
                loss = loss_fn(outputs, labels)
            
            # Backward pass with gradient scaling
            self.scaler.scale(loss).backward()
            self.scaler.step(optimizer)
            self.scaler.update()
            
            optimizer.zero_grad()
            
            return loss.item()
        
        except Exception as e:
            logger.error(f"Training optimization failed: {str(e)}")
            
            # Fallback to normal training
            outputs = model(**inputs)
            loss = loss_fn(outputs, labels)
            loss.backward()
            optimizer.step()
            optimizer.zero_grad()
            
            return loss.item()
    
    async def cache_results(
        self,
        key: str,
        data: Dict,
        ttl: Optional[int] = None
    ):
        """Cache results in Redis."""
        try:
            await self.redis.setex(
                key,
                ttl or self.cache_ttl,
                json.dumps(data)
            )
        except Exception as e:
            logger.error(f"Caching failed: {str(e)}")
    
    async def get_cached_results(self, key: str) -> Optional[Dict]:
        """Get cached results from Redis."""
        try:
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Cache retrieval failed: {str(e)}")
            return None
    
    async def measure_performance(self) -> PerformanceMetrics:
        """Measure system performance metrics."""
        try:
            # Measure throughput
            start_time = time.time()
            processed_count = await self._get_processed_count()
            throughput = processed_count / (time.time() - start_time)
            
            # Measure latency
            latency = await self._measure_average_latency()
            
            # Measure resource usage
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024
            gpu_usage = torch.cuda.memory_allocated() / torch.cuda.max_memory_allocated() if torch.cuda.is_available() else 0
            
            # Measure cache performance
            cache_hit_rate = await self._measure_cache_hit_rate()
            
            return PerformanceMetrics(
                throughput=throughput,
                latency=latency,
                memory_usage=memory_usage,
                gpu_usage=gpu_usage,
                cache_hit_rate=cache_hit_rate
            )
        
        except Exception as e:
            logger.error(f"Performance measurement failed: {str(e)}")
            return PerformanceMetrics(0, 0, 0, 0, 0)
    
    async def _process_in_parallel(self, df: dd.DataFrame) -> dd.DataFrame:
        """Process data in parallel using Dask."""
        return df.map_partitions(
            self._process_partition,
            meta=df.dtypes
        )
    
    def _process_partition(self, partition: pd.DataFrame) -> pd.DataFrame:
        """Process a single partition of data."""
        # Implement partition processing logic here
        return partition
    
    async def _get_processed_count(self) -> int:
        """Get count of processed articles."""
        try:
            result = await self.es.count(
                index="nuclear_news_processed"
            )
            return result["count"]
        except Exception as e:
            logger.error(f"Failed to get processed count: {str(e)}")
            return 0
    
    async def _measure_average_latency(self) -> float:
        """Measure average processing latency."""
        try:
            result = await self.es.search(
                index="processing_metrics",
                body={
                    "aggs": {
                        "avg_latency": {
                            "avg": {
                                "field": "processing_time"
                            }
                        }
                    }
                }
            )
            return result["aggregations"]["avg_latency"]["value"] or 0
        except Exception as e:
            logger.error(f"Failed to measure latency: {str(e)}")
            return 0
    
    async def _measure_cache_hit_rate(self) -> float:
        """Measure cache hit rate."""
        try:
            info = await self.redis.info()
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            total = hits + misses
            return (hits / total) * 100 if total > 0 else 0
        except Exception as e:
            logger.error(f"Failed to measure cache hit rate: {str(e)}")
            return 0
