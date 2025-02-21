# Nuclear Energy News Analysis Pipeline

## Overview
This document describes the NLP analysis pipeline for processing nuclear energy news articles from Bloomberg and IAEA sources.

## Pipeline Components

### 1. Text Preprocessing (`src/preprocessing/text_cleaner.py`)
- **Text Cleaning**
  - Remove URLs
  - Convert to lowercase
  - Remove punctuation
  - Remove stopwords (including domain-specific ones)
  - Lemmatization
- **Feature Extraction**
  - Named Entity Recognition (NER) using spaCy
  - Sentence segmentation
  - Part-of-speech (POS) tagging

### 2. Article Analysis (`src/analysis/`)

#### Base Analysis (`article_analyzer.py`)
- Sentiment analysis using NLTK's VADER
- Keyword extraction
- Source distribution analysis
- Visualization generation

#### Specialized Analysis
- **Semantic Analysis** (`semantic_analysis.py`): Analyzes meaning and context
- **Sentiment Analysis** (`sentiment_analysis.py`): Detailed sentiment tracking
- **Temporal Analysis** (`temporal_analysis.py`): Time-based trends
- **Geographic Analysis** (`geo_analysis.py`): Location-based analysis
- **Topic Modeling** (`topic_modeling.py`): Identifies main themes

### 3. Database Structure (`src/database/models.py`)
- Separate tables for Bloomberg and IAEA articles
- Common schema:
  ```sql
  - id (PRIMARY KEY)
  - title (TEXT)
  - content (TEXT)
  - published_date (TEXT)
  - url (TEXT UNIQUE)
  - source (TEXT)
  - created_at (TIMESTAMP)
  ```

## Analysis Process

1. **Data Loading**
   - Load articles from both Bloomberg and IAEA tables
   - Track source database for each article
   - Process in batches of 100 articles

2. **Text Preprocessing**
   - Clean and normalize text
   - Extract named entities
   - Segment into sentences
   - Custom nuclear-related stopwords removal

3. **Analysis**
   - Generate separate reports for:
     - Bloomberg articles
     - IAEA articles
     - Combined analysis
   - Create visualizations:
     - Source distribution
     - Sentiment distribution
     - Keyword word clouds

4. **Output**
   - Analysis reports in Markdown format
   - Visualizations saved in `data/analysis/`
   - Monthly statistics tracking

## Usage

Run the analysis:
```bash
uv run analyze_articles.py
```

## Output Files

### Reports
- `data/analysis/bloomberg_report.md`: Bloomberg-specific analysis
- `data/analysis/iaea_report.md`: IAEA-specific analysis
- `data/analysis/combined_report.md`: Combined analysis

### Visualizations
- `data/analysis/source_distribution.png`
- `data/analysis/sentiment_distribution.png`
- `data/analysis/keyword_wordcloud.png`

## Dependencies
- NLTK
- spaCy
- pandas
- matplotlib
- wordcloud
- tqdm

## Notes
- The pipeline is designed to handle large datasets (15,000+ articles)
- Batch processing is used to manage memory usage
- Custom nuclear domain stopwords improve analysis quality
