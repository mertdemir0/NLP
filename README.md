# Nuclear Energy Sentiment Analysis System

A sophisticated natural language processing system for analyzing nuclear energy-related content using advanced deep learning techniques and continuous learning.

## 🚀 Features

### Advanced Sentiment Analysis
- Custom BERT model fine-tuned for nuclear energy domain
- Multi-lingual support (EN, FR, DE, ES, IT)
- Aspect-based sentiment analysis:
  - Safety
  - Cost
  - Environmental impact
  - Technology
  - Policy
  - Public opinion

### Continuous Learning
- Automated model retraining
- Data quality validation
- Performance monitoring
- MLflow experiment tracking
- Model versioning

### Data Processing
- Multi-source content extraction
- Advanced text cleaning
- Parallel processing
- Efficient storage with Elasticsearch
- Redis caching for fast access

### Quality Monitoring
- Real-time metrics tracking
- Data drift detection
- Automated alerts
- Performance monitoring
- Prometheus/Grafana dashboards

### Performance Optimization
- Mixed precision training
- Batch processing
- Distributed computing
- Resource monitoring
- Caching strategies

## 🛠 Installation

### Prerequisites
- Python 3.9+
- Docker
- CUDA-capable GPU (recommended)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/nuclear-sentiment
cd nuclear-sentiment
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start required services:
```bash
# Start Elasticsearch
docker run -d -p 9200:9200 -e "discovery.type=single-node" elasticsearch:8.11.0

# Start Redis
docker run -d -p 6379:6379 redis:5.0.1

# Start MLflow
mlflow server --host 0.0.0.0 --port 5000

# Start Prometheus
prometheus --config.file=prometheus.yml
```

5. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## 📊 Usage

### Basic Usage

```python
from src.models.nuclear_bert import NuclearBERTModel
from src.data.processor import DataProcessor

# Initialize model and processor
model = NuclearBERTModel()
processor = DataProcessor()

# Analyze sentiment
text = "Nuclear energy plays a crucial role in reducing carbon emissions."
result = model.predict(text)
print(f"Overall sentiment: {result.sentiment}")
print(f"Aspect sentiments: {result.aspects}")
```

### Continuous Learning

```python
from src.training.continuous_learning import ContinuousLearningPipeline

# Initialize pipeline
pipeline = ContinuousLearningPipeline()

# Start continuous learning
await pipeline.run()
```

### Monitoring

```python
from src.monitoring.quality_monitor import QualityMonitor

# Initialize monitor
monitor = QualityMonitor()

# Check data quality
metrics = await monitor.check_data_quality(data)
print(f"Quality metrics: {metrics}")
```

## 📈 Dashboards

### Grafana Dashboards
- Model Performance: `http://localhost:3000/d/model-performance`
- Data Quality: `http://localhost:3000/d/data-quality`
- System Metrics: `http://localhost:3000/d/system-metrics`

### MLflow UI
Access experiment tracking at `http://localhost:5000`

## 🔧 Configuration

### Model Configuration
Edit `config/model_config.yaml` to configure:
- Model architecture
- Training parameters
- Inference settings

### System Configuration
Edit `config/system_config.yaml` to configure:
- Data processing
- Monitoring
- Alerts
- Performance optimization

## 📝 Documentation

Detailed documentation is available in the `docs` directory:
- [API Reference](docs/API.md)
- [Model Architecture](docs/MODEL.md)
- [Data Processing](docs/DATA_PROCESSING.md)
- [Monitoring](docs/MONITORING.md)
- [Configuration Guide](docs/CONFIGURATION.md)

## 🧪 Testing

Run tests:
```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/models/test_nuclear_bert.py
```

## 📊 Performance

### Hardware Requirements
- Minimum: 16GB RAM, 4 CPU cores
- Recommended: 32GB RAM, 8 CPU cores, NVIDIA GPU with 8GB+ VRAM

### Benchmarks
- Processing Speed: ~1000 articles/minute
- Model Inference: ~100ms/article
- Training: ~2 hours/epoch on recommended hardware

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Bloomberg API for data access
- Hugging Face for transformer models
- ElasticSearch for efficient storage
- Redis for caching
- Prometheus/Grafana for monitoring
