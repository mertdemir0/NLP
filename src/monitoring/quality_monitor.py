"""
Quality monitoring system for nuclear sentiment analysis.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import logging
from prometheus_client import start_http_server, Gauge, Counter, Histogram
import json
from elasticsearch import AsyncElasticsearch
import aiohttp
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class QualityMonitor:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Initialize Elasticsearch client
        self.es = AsyncElasticsearch([
            self.config.get("elasticsearch_url", "http://localhost:9200")
        ])
        
        # Initialize Prometheus metrics
        self.data_quality_score = Gauge(
            "nuclear_sentiment_data_quality",
            "Data quality score for nuclear sentiment analysis"
        )
        self.model_performance = Gauge(
            "nuclear_sentiment_model_performance",
            "Model performance metrics",
            ["metric"]
        )
        self.processing_time = Histogram(
            "nuclear_sentiment_processing_time",
            "Processing time for sentiment analysis",
            buckets=(1, 5, 10, 30, 60, 120, 300, 600)
        )
        self.error_counter = Counter(
            "nuclear_sentiment_errors",
            "Error counter for sentiment analysis",
            ["type"]
        )
        
        # Start Prometheus server
        start_http_server(
            self.config.get("prometheus_port", 9090)
        )
    
    async def check_data_quality(self, data: pd.DataFrame) -> Dict[str, float]:
        """Check data quality using Evidently."""
        try:
            # Create data quality report
            report = Report(metrics=[
                DataQualityPreset(),
                DataDriftPreset()
            ])
            
            report.run(
                reference_data=await self._get_reference_data(),
                current_data=data
            )
            
            # Extract metrics
            metrics = {}
            for metric in report.metrics:
                metrics.update(metric.get_metrics())
            
            # Update Prometheus metrics
            self.data_quality_score.set(metrics.get("data_quality_score", 0))
            
            # Log results
            logger.info(f"Data quality metrics: {metrics}")
            
            # Store results in Elasticsearch
            await self._store_quality_metrics(metrics)
            
            return metrics
        
        except Exception as e:
            logger.error(f"Data quality check failed: {str(e)}")
            self.error_counter.labels(type="data_quality").inc()
            return {}
    
    async def monitor_model_performance(
        self,
        predictions: np.ndarray,
        labels: np.ndarray
    ) -> Dict[str, float]:
        """Monitor model performance metrics."""
        try:
            # Calculate metrics
            metrics = {
                "accuracy": np.mean(predictions == labels),
                "f1_score": self._calculate_f1(predictions, labels),
                "mse": np.mean((predictions - labels) ** 2)
            }
            
            # Update Prometheus metrics
            for metric, value in metrics.items():
                self.model_performance.labels(metric=metric).set(value)
            
            # Store metrics in Elasticsearch
            await self._store_performance_metrics(metrics)
            
            return metrics
        
        except Exception as e:
            logger.error(f"Performance monitoring failed: {str(e)}")
            self.error_counter.labels(type="performance_monitoring").inc()
            return {}
    
    async def send_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "warning"
    ):
        """Send alert to configured channels."""
        try:
            # Prepare alert payload
            alert = {
                "type": alert_type,
                "message": message,
                "severity": severity,
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to Slack
            if "slack_webhook" in self.config:
                await self._send_slack_alert(alert)
            
            # Send email
            if "email_config" in self.config:
                await self._send_email_alert(alert)
            
            # Store alert in Elasticsearch
            await self._store_alert(alert)
        
        except Exception as e:
            logger.error(f"Alert sending failed: {str(e)}")
            self.error_counter.labels(type="alert").inc()
    
    async def _get_reference_data(self) -> pd.DataFrame:
        """Get reference data for quality comparison."""
        try:
            result = await self.es.search(
                index="nuclear_news_processed",
                body={
                    "query": {
                        "range": {
                            "processed_date": {
                                "gte": "now-30d/d"
                            }
                        }
                    }
                },
                size=10000
            )
            
            return pd.DataFrame([
                hit["_source"] for hit in result["hits"]["hits"]
            ])
        
        except Exception as e:
            logger.error(f"Failed to get reference data: {str(e)}")
            return pd.DataFrame()
    
    async def _store_quality_metrics(self, metrics: Dict):
        """Store quality metrics in Elasticsearch."""
        try:
            await self.es.index(
                index="quality_metrics",
                document={
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics
                }
            )
        except Exception as e:
            logger.error(f"Failed to store quality metrics: {str(e)}")
    
    async def _store_performance_metrics(self, metrics: Dict):
        """Store performance metrics in Elasticsearch."""
        try:
            await self.es.index(
                index="model_metrics",
                document={
                    "timestamp": datetime.now().isoformat(),
                    "metrics": metrics
                }
            )
        except Exception as e:
            logger.error(f"Failed to store performance metrics: {str(e)}")
    
    async def _store_alert(self, alert: Dict):
        """Store alert in Elasticsearch."""
        try:
            await self.es.index(
                index="alerts",
                document=alert
            )
        except Exception as e:
            logger.error(f"Failed to store alert: {str(e)}")
    
    async def _send_slack_alert(self, alert: Dict):
        """Send alert to Slack."""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    self.config["slack_webhook"],
                    json={
                        "text": f"*{alert['type']}*: {alert['message']}\nSeverity: {alert['severity']}"
                    }
                )
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {str(e)}")
    
    async def _send_email_alert(self, alert: Dict):
        """Send alert via email."""
        # Implement email sending logic here
        pass
    
    def _calculate_f1(
        self,
        predictions: np.ndarray,
        labels: np.ndarray
    ) -> float:
        """Calculate F1 score."""
        try:
            true_positives = np.sum((predictions == 1) & (labels == 1))
            false_positives = np.sum((predictions == 1) & (labels == 0))
            false_negatives = np.sum((predictions == 0) & (labels == 1))
            
            precision = true_positives / (true_positives + false_positives)
            recall = true_positives / (true_positives + false_negatives)
            
            return 2 * (precision * recall) / (precision + recall)
        
        except:
            return 0.0
