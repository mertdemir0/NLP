# Nuclear Energy Content Analysis Documentation

This documentation provides detailed information about the Nuclear Energy Content Analysis project, its components, and usage instructions.

## Table of Contents
1. [Overview](#overview)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Components](#components)
6. [API Reference](#api-reference)
7. [Examples](#examples)

## Overview

The Nuclear Energy Content Analysis project is a comprehensive NLP pipeline designed to analyze nuclear energy-related articles from Bloomberg. The system performs various types of analysis including sentiment analysis, topic modeling, semantic analysis, temporal analysis, and geographical analysis.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/mertdemir0/NLP.git
cd NLP
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

## Configuration

The system is configured through YAML files in the `config/` directory:

- `config.yaml`: Main configuration file
- `country_coordinates.json`: Geographical coordinates for location analysis

### Environment Variables

Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

Required environment variables:
- `BLOOMBERG_API_KEY`: Your Bloomberg API key
- `LOG_LEVEL`: Logging level (default: INFO)

## Usage

### Command Line Interface

Run the complete pipeline:
```bash
python -m src.main --config config/config.yaml --input-dir data/raw --output-dir output --dashboard
```

Options:
- `--config`: Path to configuration file
- `--input-dir`: Directory containing input files
- `--output-dir`: Directory for output files
- `--log-level`: Logging level
- `--dashboard`: Launch interactive dashboard

### Interactive Dashboard

Launch the dashboard:
```bash
python -m src.visualization.dashboard
```

## Components

### 1. Data Ingestion
- PDF document parsing
- HTML content extraction
- URL content fetching
- Metadata extraction

### 2. Analysis
- Sentiment Analysis
- Topic Modeling
- Semantic Analysis
- Temporal Analysis
- Geographical Analysis

### 3. Visualization
- Interactive Dashboard
- Report Generation
- Data Export

## API Reference

### Data Ingestion

```python
from src.data_ingestion import DataIngestion

ingestion = DataIngestion()
results = ingestion.ingest_directory('data/raw')
```

### Analysis

```python
from src.analysis import SentimentAnalyzer, TopicModeler

# Sentiment Analysis
analyzer = SentimentAnalyzer()
results = analyzer.analyze(texts)

# Topic Modeling
modeler = TopicModeler()
topics = modeler.analyze(texts)
```

### Visualization

```python
from src.visualization import NuclearEnergyDashboard

dashboard = NuclearEnergyDashboard()
dashboard.load_data('output')
dashboard.run()
```

## Examples

### Basic Usage

```python
from src.main import run_pipeline
import yaml

# Load configuration
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Run pipeline
results = run_pipeline(config, 'data/raw', 'output')
```

### Custom Analysis

```python
from src.analysis import TemporalAnalyzer

analyzer = TemporalAnalyzer()
results = analyzer.analyze_content_volume(texts, time_window='monthly')
```
