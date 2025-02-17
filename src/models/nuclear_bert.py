"""
Nuclear energy-specific BERT model for sentiment analysis.
"""

import torch
from torch import nn
from transformers import BertModel, BertTokenizer, AdamW
from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class SentimentOutput:
    sentiment: float
    aspects: Dict[str, float]
    confidence: float
    entities: List[Dict[str, str]]

class NuclearBERTModel(nn.Module):
    def __init__(
        self,
        model_name: str = "bert-base-multilingual-cased",
        num_aspects: int = 6,
        device: Optional[str] = None
    ):
        super().__init__()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.bert = BertModel.from_pretrained(model_name)
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        
        # Sentiment head
        self.sentiment_head = nn.Sequential(
            nn.Linear(self.bert.config.hidden_size, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 1),
            nn.Tanh()
        )
        
        # Aspect head
        self.aspect_head = nn.Sequential(
            nn.Linear(self.bert.config.hidden_size, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, num_aspects),
            nn.Tanh()
        )
        
        self.to(self.device)
    
    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            return_dict=True
        )
        
        pooled_output = outputs.pooler_output
        
        sentiment = self.sentiment_head(pooled_output)
        aspects = self.aspect_head(pooled_output)
        
        return sentiment, aspects
    
    def predict(self, text: str) -> SentimentOutput:
        self.eval()
        with torch.no_grad():
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                max_length=512,
                truncation=True,
                padding=True
            ).to(self.device)
            
            sentiment, aspects = self(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"]
            )
            
            # Convert to probabilities
            sentiment_score = sentiment.item()
            aspect_scores = aspects.squeeze().cpu().numpy()
            
            # Calculate confidence
            confidence = 1.0 - np.std(aspect_scores)
            
            # Extract entities (placeholder for now)
            entities = []
            
            return SentimentOutput(
                sentiment=sentiment_score,
                aspects={
                    "safety": aspect_scores[0],
                    "cost": aspect_scores[1],
                    "environmental_impact": aspect_scores[2],
                    "technology": aspect_scores[3],
                    "policy": aspect_scores[4],
                    "public_opinion": aspect_scores[5]
                },
                confidence=confidence,
                entities=entities
            )
    
    def train_step(
        self,
        batch: Dict[str, torch.Tensor],
        optimizer: AdamW
    ) -> Dict[str, float]:
        self.train()
        
        input_ids = batch["input_ids"].to(self.device)
        attention_mask = batch["attention_mask"].to(self.device)
        sentiment_labels = batch["sentiment"].to(self.device)
        aspect_labels = batch["aspects"].to(self.device)
        
        optimizer.zero_grad()
        
        sentiment_pred, aspect_pred = self(input_ids, attention_mask)
        
        # Calculate losses
        sentiment_loss = nn.MSELoss()(sentiment_pred, sentiment_labels)
        aspect_loss = nn.MSELoss()(aspect_pred, aspect_labels)
        
        # Combined loss
        total_loss = sentiment_loss + 0.5 * aspect_loss
        
        total_loss.backward()
        optimizer.step()
        
        return {
            "total_loss": total_loss.item(),
            "sentiment_loss": sentiment_loss.item(),
            "aspect_loss": aspect_loss.item()
        }
    
    def save(self, path: str):
        """Save model and tokenizer."""
        torch.save(self.state_dict(), f"{path}/model.pt")
        self.tokenizer.save_pretrained(path)
        logger.info(f"Model saved to {path}")
    
    def load(self, path: str):
        """Load model and tokenizer."""
        self.load_state_dict(torch.load(f"{path}/model.pt"))
        self.tokenizer = BertTokenizer.from_pretrained(path)
        logger.info(f"Model loaded from {path}")
