# NLP Project

A comprehensive Natural Language Processing (NLP) toolkit that provides various text analysis capabilities including sentiment analysis, topic modeling, and semantic analysis.

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
│   │   └── topic_modeling.py
│   ├── data_ingestion/  # Data input handling
│   │   ├── html_parser.py
│   │   ├── ingestion.py
│   │   └── pdf_parser.py
│   ├── preprocessing/   # Text preprocessing
│   │   └── text_cleaner.py
│   ├── utils/          # Utility functions
│   │   ├── config.py
│   │   └── logger.py
│   └── visualization/  # Data visualization
│       ├── dashboard.py
│       └── report_generator.py
└── tests/           # Test files
```

## Features

- **Data Ingestion**: Support for multiple input formats including HTML and PDF
- **Text Analysis**:
  - Keyword Extraction
  - Semantic Analysis
  - Sentiment Analysis
  - Topic Modeling
- **Text Preprocessing**: Text cleaning and normalization
- **Visualization**: Interactive dashboard and report generation capabilities

## Getting Started

1. Set up your environment variables in the `.env` file
2. Install the required dependencies
3. Run the main application using `python src/main.py`

## Testing

The project includes a test suite in the `tests/` directory to ensure code quality and functionality.

## Documentation

Detailed documentation is available in the `docs/` directory.

## Configuration

Project configuration can be managed through files in the `config/` directory and environment variables.
