# User Guide

## Getting Started

### Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and configure your environment variables

### Basic Usage

#### 1. Data Ingestion

```python
from src.data_ingestion import HTMLParser, PDFParser

# Parse HTML content
html_parser = HTMLParser()
html_data = html_parser.parse("path/to/file.html")

# Parse PDF content
pdf_parser = PDFParser()
pdf_data = pdf_parser.parse("path/to/file.pdf")
```

#### 2. Text Analysis

```python
from src.analysis import SentimentAnalyzer, TopicModeler

# Analyze sentiment
sentiment_analyzer = SentimentAnalyzer()
sentiment = sentiment_analyzer.analyze(text)

# Extract topics
topic_modeler = TopicModeler()
topics = topic_modeler.extract_topics(text)
```

#### 3. Visualization

```python
from src.visualization import Dashboard, ReportGenerator

# Generate visual report
report = ReportGenerator()
report.create("path/to/output.pdf")

# Launch dashboard
dashboard = Dashboard()
dashboard.start()
```

## Advanced Features

### Custom Preprocessing

```python
from src.preprocessing import TextCleaner

cleaner = TextCleaner(
    remove_stopwords=True,
    lemmatize=True,
    custom_tokens=['custom1', 'custom2']
)
cleaned_text = cleaner.clean(text)
```

### Configuration

#### Environment Variables

Required environment variables in `.env`:
```
API_KEY=your_api_key
MODEL_PATH=/path/to/models
LOG_LEVEL=INFO
```

#### Runtime Configuration

```python
from src.utils import config

config.set('model.parameters.threshold', 0.75)
config.set('output.format', 'json')
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**
   - Ensure virtual environment is activated
   - Verify all dependencies are installed

2. **FileNotFoundError**
   - Check file paths in configuration
   - Verify model files are downloaded

3. **API Errors**
   - Verify API key in `.env`
   - Check API endpoint status

### Logging

Logs are stored in `logs/` directory. Set log level in `.env`:
```
LOG_LEVEL=DEBUG  # For detailed logging
LOG_LEVEL=INFO   # For standard logging
```

## Best Practices

1. Always preprocess text before analysis
2. Use appropriate model parameters for your use case
3. Regularly update model weights
4. Monitor system resources during batch processing
5. Implement error handling for production use