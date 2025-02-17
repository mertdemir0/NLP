"""
Continuous learning pipeline for nuclear sentiment analysis.
"""

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
import torch
from transformers import AdamW
import mlflow
from deepchecks.nlp.suites import TrainingValidationSuite
import numpy as np

from src.models.nuclear_bert import NuclearBERTModel
from src.data.processor import DataProcessor
from src.utils.metrics import calculate_metrics

logger = logging.getLogger(__name__)

class ModelValidator:
    def __init__(self):
        self.suite = TrainingValidationSuite()
    
    async def validate_data(self, data: Dict) -> float:
        """Validate data quality."""
        try:
            # Run deepchecks validation
            validation_result = self.suite.run(data)
            
            # Calculate quality score based on check results
            failed_checks = validation_result.get_not_passed_checks()
            quality_score = 1.0 - (len(failed_checks) / len(self.suite.checks))
            
            logger.info(f"Data quality score: {quality_score:.2f}")
            return quality_score
        
        except Exception as e:
            logger.error(f"Data validation failed: {str(e)}")
            return 0.0
    
    async def evaluate_model(
        self,
        model: NuclearBERTModel,
        eval_data: Dict
    ) -> Dict[str, float]:
        """Evaluate model performance."""
        model.eval()
        metrics = {}
        
        try:
            with torch.no_grad():
                predictions = []
                labels = []
                
                for batch in eval_data:
                    sentiment_pred, _ = model(
                        batch["input_ids"],
                        batch["attention_mask"]
                    )
                    predictions.extend(sentiment_pred.cpu().numpy())
                    labels.extend(batch["sentiment"].cpu().numpy())
                
                metrics = calculate_metrics(
                    np.array(predictions),
                    np.array(labels)
                )
                
                logger.info(f"Model evaluation metrics: {metrics}")
                return metrics
        
        except Exception as e:
            logger.error(f"Model evaluation failed: {str(e)}")
            return metrics

class ContinuousLearningPipeline:
    def __init__(
        self,
        model: Optional[NuclearBERTModel] = None,
        data_processor: Optional[DataProcessor] = None,
        config: Optional[Dict] = None
    ):
        self.model = model or NuclearBERTModel()
        self.data_processor = data_processor or DataProcessor()
        self.validator = ModelValidator()
        self.config = config or {}
        
        # MLflow setup
        mlflow.set_tracking_uri(self.config.get("mlflow_uri", "http://localhost:5000"))
        
        self.new_data_threshold = self.config.get("new_data_threshold", 10000)
        self.performance_threshold = self.config.get("performance_threshold", 0.85)
        self.quality_threshold = self.config.get("quality_threshold", 0.9)
    
    async def should_retrain(self) -> bool:
        """Check if model should be retrained."""
        try:
            # Check data volume
            new_data_count = await self.data_processor.get_new_data_count()
            if new_data_count < self.new_data_threshold:
                return False
            
            # Check time since last training
            last_training = await self.data_processor.get_last_training_time()
            if last_training:
                time_diff = datetime.now() - last_training
                if time_diff < timedelta(days=7):
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error checking retrain conditions: {str(e)}")
            return False
    
    async def retrain(self) -> bool:
        """Retrain the model with new data."""
        try:
            logger.info("Starting model retraining")
            
            # Start MLflow run
            with mlflow.start_run():
                # Get new data
                train_data = await self.data_processor.get_new_data()
                
                # Validate data quality
                quality_score = await self.validator.validate_data(train_data)
                if quality_score < self.quality_threshold:
                    logger.warning(f"Data quality below threshold: {quality_score:.2f}")
                    return False
                
                # Train model
                optimizer = AdamW(
                    self.model.parameters(),
                    lr=self.config.get("learning_rate", 2e-5)
                )
                
                for epoch in range(self.config.get("num_epochs", 3)):
                    epoch_loss = 0
                    for batch in train_data:
                        loss_dict = self.model.train_step(batch, optimizer)
                        epoch_loss += loss_dict["total_loss"]
                    
                    logger.info(f"Epoch {epoch + 1} loss: {epoch_loss:.4f}")
                    mlflow.log_metric("epoch_loss", epoch_loss, step=epoch)
                
                # Evaluate model
                eval_data = await self.data_processor.get_eval_data()
                metrics = await self.validator.evaluate_model(self.model, eval_data)
                
                # Log metrics
                for metric_name, value in metrics.items():
                    mlflow.log_metric(metric_name, value)
                
                # Check performance
                if metrics.get("f1_score", 0) < self.performance_threshold:
                    logger.warning("Model performance below threshold")
                    return False
                
                # Save model
                model_path = f"models/nuclear_bert_{datetime.now().strftime('%Y%m%d_%H%M')}"
                self.model.save(model_path)
                mlflow.log_artifact(model_path)
                
                logger.info("Model retraining completed successfully")
                return True
        
        except Exception as e:
            logger.error(f"Model retraining failed: {str(e)}")
            return False
    
    async def run(self):
        """Run the continuous learning pipeline."""
        while True:
            try:
                if await self.should_retrain():
                    success = await self.retrain()
                    if success:
                        logger.info("Successfully updated model")
                    else:
                        logger.warning("Model update failed quality checks")
                
                # Wait before next check
                await asyncio.sleep(3600)  # Check every hour
            
            except Exception as e:
                logger.error(f"Pipeline run failed: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
