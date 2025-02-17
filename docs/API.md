# API Reference

## Data Ingestion

### DataIngestion

Main class for handling data ingestion from various sources.

```python
from src.data_ingestion import DataIngestion

ingestion = DataIngestion(config)
```

#### Methods

- `ingest_directory(input_dir: str) -> List[Dict]`: Process all files in a directory
- `ingest_file(file_path: str) -> Dict`: Process a single file
- `save_results(results: List[Dict], output_dir: str)`: Save ingestion results

### PDFParser

Handles PDF document parsing and content extraction.

```python
from src.data_ingestion import PDFParser

parser = PDFParser()
```

#### Methods

- `parse(file_path: str) -> Dict`: Parse PDF file
- `extract_metadata(pdf) -> Dict`: Extract PDF metadata
- `extract_text(pdf) -> str`: Extract text content

### HTMLParser

Handles HTML content parsing from files and URLs.

```python
from src.data_ingestion import HTMLParser

parser = HTMLParser()
```

#### Methods

- `parse(source: str) -> Dict`: Parse HTML content
- `parse_url(url: str) -> Dict`: Parse content from URL
- `parse_file(file_path: str) -> Dict`: Parse HTML file

## Analysis

### SentimentAnalyzer

Performs sentiment analysis on text content.

```python
from src.analysis import SentimentAnalyzer

analyzer = SentimentAnalyzer()
```

#### Methods

- `analyze(texts: List[Dict]) -> Dict`: Analyze sentiment
- `get_sentiment_scores(text: str) -> Dict`: Get sentiment scores
- `analyze_trends(results: Dict) -> Dict`: Analyze sentiment trends

### TopicModeler

Performs topic modeling on text content.

```python
from src.analysis import TopicModeler

modeler = TopicModeler()
```

#### Methods

- `analyze(texts: List[Dict]) -> Dict`: Extract topics
- `train_model(texts: List[str])`: Train topic model
- `get_topics(n_topics: int) -> List[Dict]`: Get top topics

### SemanticAnalyzer

Performs semantic analysis and clustering.

```python
from src.analysis import SemanticAnalyzer

analyzer = SemanticAnalyzer()
```

#### Methods

- `analyze(texts: List[Dict]) -> Dict`: Analyze semantics
- `cluster_documents(embeddings: np.ndarray) -> Dict`: Cluster documents
- `get_document_similarity(doc1: str, doc2: str) -> float`: Get similarity score

### TemporalAnalyzer

Analyzes temporal patterns in content.

```python
from src.analysis import TemporalAnalyzer

analyzer = TemporalAnalyzer()
```

#### Methods

- `analyze(texts: List[Dict]) -> Dict`: Analyze temporal patterns
- `analyze_volume(texts: List[Dict], window: str) -> Dict`: Analyze content volume
- `detect_trends(data: Dict) -> List[Dict]`: Detect temporal trends

### GeoAnalyzer

Performs geographical analysis of content.

```python
from src.analysis import GeoAnalyzer

analyzer = GeoAnalyzer()
```

#### Methods

- `analyze(texts: List[Dict]) -> Dict`: Analyze geographical patterns
- `extract_locations(text: str) -> List[str]`: Extract location mentions
- `create_heatmap(locations: List[Dict]) -> Dict`: Create location heatmap

## Visualization

### NuclearEnergyDashboard

Interactive dashboard for data visualization.

```python
from src.visualization import NuclearEnergyDashboard

dashboard = NuclearEnergyDashboard(config)
```

#### Methods

- `load_data(data_dir: str)`: Load analysis results
- `run()`: Launch dashboard
- `update_visualizations()`: Update dashboard components

### ReportGenerator

Generates analysis reports in various formats.

```python
from src.visualization import ReportGenerator

generator = ReportGenerator(config)
```

#### Methods

- `generate_report(results: Dict, output_dir: str)`: Generate complete report
- `generate_html_report(results: Dict) -> str`: Generate HTML report
- `generate_markdown_report(results: Dict) -> str`: Generate Markdown report

## Preprocessing

### TextCleaner

Cleans and normalizes text content.

```python
from src.preprocessing import TextCleaner

cleaner = TextCleaner()
```

#### Methods

- `clean(text: str) -> str`: Clean text content
- `remove_noise(text: str) -> str`: Remove noise from text
- `normalize_whitespace(text: str) -> str`: Normalize whitespace

### Tokenizer

Handles text tokenization.

```python
from src.preprocessing import Tokenizer

tokenizer = Tokenizer()
```

#### Methods

- `tokenize(text: str) -> List[str]`: Tokenize text
- `split_sentences(text: str) -> List[str]`: Split into sentences
- `get_ngrams(tokens: List[str], n: int) -> List[str]`: Get n-grams

### Normalizer

Normalizes text and tokens.

```python
from src.preprocessing import Normalizer

normalizer = Normalizer()
```

#### Methods

- `normalize(tokens: List[str]) -> List[str]`: Normalize tokens
- `lemmatize(tokens: List[str]) -> List[str]`: Lemmatize tokens
- `stem(tokens: List[str]) -> List[str]`: Stem tokens
