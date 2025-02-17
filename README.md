# Nuclear Energy Content Analysis

A comprehensive Natural Language Processing (NLP) toolkit for analyzing nuclear energy-related articles, providing various text analysis capabilities including sentiment analysis, topic modeling, semantic analysis, temporal analysis, and geographical analysis.

## Table of Contents
1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Features](#features)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Usage](#usage)
7. [Components](#components)
8. [Testing](#testing)
9. [Documentation](#documentation)
10. [Contributing](#contributing)

## Overview

The Nuclear Energy Content Analysis project is a comprehensive NLP pipeline designed to analyze nuclear energy-related articles from Bloomberg. The system performs various types of analysis including sentiment analysis, topic modeling, semantic analysis, temporal analysis, and geographical analysis.

## Project Structure

```
├── config/           # Configuration files
├── data/            # Data storage directory
├── docs/            # Documentation files
├── scripts/         # Utility scripts
├── src/             # Source code
│   ├── analysis/    # Text analysis modules
│   │   ├── keyword_extraction.py
│   │   ├── semantic_analysis.py
│   │   ├── sentiment_analysis.py
│   │   ├── temporal_analysis.py
│   │   ├── geo_analysis.py
│   │   └── topic_modeling.py
│   ├── data_ingestion/  # Data input handling
│   │   ├── html_parser.py
│   │   ├── ingestion.py
│   │   └── pdf_parser.py
│   ├── preprocessing/   # Text preprocessing
│   │   ├── text_cleaner.py
│   │   ├── tokenizer.py
│   │   └── normalizer.py
│   ├── utils/          # Utility functions
│   │   ├── config.py
│   │   └── logger.py
│   └── visualization/  # Data visualization
│       ├── dashboard.py
│       └── report_generator.py
└── tests/           # Test files
```

## Features

- **Data Ingestion**: 
  - Support for multiple input formats (HTML, PDF)
  - URL content fetching
  - Metadata extraction
  - Concurrent processing

- **Text Analysis**:
  - Sentiment Analysis
  - Topic Modeling
  - Semantic Analysis
  - Temporal Analysis
  - Geographical Analysis
  - Keyword Extraction

- **Text Preprocessing**: 
  - Text cleaning
  - Tokenization
  - Normalization
  - Noise removal

- **Visualization**: 
  - Interactive Dash Dashboard
  - Geographical heatmaps
  - Temporal charts
  - Technology distribution visualizations
  - Report generation in multiple formats

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

The system is configured through files in the `config/` directory:

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

## Testing

The project includes a comprehensive test suite in the `tests/` directory to ensure code quality and functionality. Run tests using:

```bash
pytest tests/
```

## Documentation

Detailed documentation is available in the `docs/` directory:
- `API.md`: Complete API reference
- `CONTRIBUTING.md`: Contributing guidelines

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](docs/CONTRIBUTING.md) for details on how to submit pull requests, report issues, and contribute to the project.

For API documentation and detailed examples, please refer to our [API Reference](docs/API.md).
