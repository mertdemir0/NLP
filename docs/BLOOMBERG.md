# Bloomberg API Integration

This document describes how to use the Bloomberg API integration in the Nuclear Energy Content Analysis project.

## Overview

The project uses the Bloomberg API (`blpapi`) to fetch news articles, company data, and market data related to nuclear energy. The integration is implemented in the `BloombergClient` class.

## Installation

1. Install the Bloomberg API Python SDK:
```bash
pip install blpapi
```

2. Configure Bloomberg API credentials in your `.env` file:
```bash
BLOOMBERG_USERNAME=your_username
BLOOMBERG_PASSWORD=your_password
```

## Usage

### Basic Usage

```python
from src.data_ingestion import BloombergClient
import datetime

# Initialize client
config = {
    'bloomberg_host': 'localhost',
    'bloomberg_port': 8194,
    'bloomberg_auth': {
        'username': 'your_username',
        'password': 'your_password'
    }
}

# Using context manager
with BloombergClient(config) as client:
    # Fetch news articles
    articles = client.fetch_news_articles(
        topics=["nuclear energy", "nuclear power"],
        start_date=datetime.datetime.now() - datetime.timedelta(days=30),
        languages=["en"]
    )
```

### Fetching Company Data

```python
# Fetch historical data for nuclear energy companies
companies = ["EDF FP Equity", "CEZ CP Equity"]
fields = ["PX_LAST", "VOLUME", "NEWS_SENTIMENT"]

df = client.fetch_company_data(
    companies=companies,
    fields=fields,
    start_date=datetime.datetime(2024, 1, 1)
)
```

### Real-time Market Data

```python
def market_data_callback(data):
    print(f"Received update: {data}")

# Subscribe to real-time updates
client.subscribe_to_market_data(
    securities=["EDF FP Equity"],
    fields=["LAST_PRICE", "BID", "ASK"],
    callback=market_data_callback
)
```

### Field Information

```python
# Get information about Bloomberg fields
field_info = client.get_field_info("NEWS_SENTIMENT")
print(f"Field description: {field_info['description']}")
```

### ESG Data Analysis

```python
# Fetch ESG data for nuclear energy companies
companies = ["EDF FP Equity", "CEZ CP Equity"]
df_esg = client.fetch_esg_data(
    companies=companies,
    metrics=[
        "ESG_DISCLOSURE_SCORE",
        "ENVIRONMENTAL_DISCLOSURE_SCORE",
        "CARBON_EMISSIONS_SCOPE_1"
    ]
)
```

### Nuclear Energy Indices

```python
# Fetch nuclear energy index data
df_indices = client.fetch_nuclear_indices()
print("Nuclear Energy Market Overview:")
for _, row in df_indices.iterrows():
    print(f"{row['ticker']}:")
    print(f"  Price: {row['PX_LAST']}")
    print(f"  1D Change: {row['CHG_PCT_1D']}%")
    print(f"  YTD Change: {row['CHG_PCT_YTD']}%")
```

### Sentiment Analysis

```python
# Analyze sentiment trends
topics = ["nuclear energy", "nuclear power"]
trends, stats = client.analyze_sentiment_trends(
    topics=topics,
    lookback_days=90,
    interval='weekly'
)

print("Sentiment Summary:")
print(f"Overall Sentiment: {stats['overall_sentiment']:.2f}")
print(f"Positive Articles: {stats['positive_ratio']*100:.1f}%")
print(f"Negative Articles: {stats['negative_ratio']*100:.1f}%")
```

### Company Events

```python
# Track company events
events = client.get_company_events(
    company="EDF FP Equity",
    event_types=["earnings", "regulatory_filing"],
    start_date=datetime.datetime.now()
)

print("Upcoming Events:")
for event in events:
    print(f"{event['date']}: {event['type']} - {event['description']}")
```

## Configuration

### Bloomberg Configuration File

The `config/bloomberg_config.yaml` file contains settings for the Bloomberg integration:

```yaml
# Connection settings
bloomberg_host: localhost
bloomberg_port: 8194

# Authentication
bloomberg_auth:
  username: ${BLOOMBERG_USERNAME}
  password: ${BLOOMBERG_PASSWORD}

# News search settings
news_search:
  topics:
    - "nuclear energy"
    - "nuclear power"
    - "nuclear reactor"
  max_articles_per_request: 1000
  default_date_range_days: 30

# Market data settings
market_data:
  securities:
    - "NUCLEAR INDEX"
    - "NUCLEAR ENERGY COMPANIES"
  fields:
    - "PX_LAST"
    - "VOLUME"
    - "NEWS_SENTIMENT"
  update_interval_ms: 5000

# ESG settings
esg_data:
  metrics:
    - ESG_DISCLOSURE_SCORE
    - ENVIRONMENTAL_DISCLOSURE_SCORE
    - SOCIAL_DISCLOSURE_SCORE
    - GOVERNANCE_DISCLOSURE_SCORE
    - ESG_RATING
    - CARBON_EMISSIONS_SCOPE_1
    - CARBON_EMISSIONS_SCOPE_2

# Nuclear indices settings
nuclear_indices:
  - BNEF Nuclear Index
  - S&P Global Nuclear Energy Index
  - WNA Nuclear Energy Index

# Sentiment analysis settings
sentiment_analysis:
  max_articles_per_request: 10000
  default_lookback_days: 90
  intervals:
    - daily
    - weekly
    - monthly

# Event tracking settings
event_tracking:
  types:
    - earnings
    - regulatory_filing
    - corporate_action
    - company_meeting
  default_lookback_days: 30
```

## API Reference

### BloombergClient

#### Methods

- `connect() -> bool`
  - Establishes connection to Bloomberg API
  - Returns True if successful

- `disconnect()`
  - Closes the Bloomberg API session

- `fetch_news_articles(topics: List[str], start_date: datetime, end_date: Optional[datetime] = None, max_articles: int = 1000, languages: Optional[List[str]] = None) -> List[Dict]`
  - Fetches news articles based on topics and date range
  - Returns list of article dictionaries

- `fetch_company_data(companies: List[str], fields: List[str], start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame`
  - Fetches historical company data
  - Returns pandas DataFrame

- `subscribe_to_market_data(securities: List[str], fields: List[str], callback: callable) -> bool`
  - Subscribes to real-time market data updates
  - Returns True if subscription successful

- `get_field_info(field: str) -> Dict`
  - Gets information about a Bloomberg field
  - Returns dictionary with field details

#### ESG Data Methods

- `fetch_esg_data(companies: List[str], metrics: Optional[List[str]] = None) -> pd.DataFrame`
  - Fetches ESG (Environmental, Social, Governance) data for companies
  - Default metrics include ESG scores, ratings, and carbon emissions
  - Returns pandas DataFrame with company ESG data

#### Market Data Methods

- `fetch_nuclear_indices() -> pd.DataFrame`
  - Fetches data for major nuclear energy indices
  - Includes price, volume, and performance metrics
  - Returns pandas DataFrame with index data

#### Analysis Methods

- `analyze_sentiment_trends(topics: List[str], lookback_days: int = 90, interval: str = 'daily') -> Tuple[pd.DataFrame, Dict]`
  - Analyzes sentiment trends in nuclear energy news
  - Supports daily, weekly, or monthly aggregation
  - Returns tuple of (trends DataFrame, summary statistics)

#### Event Tracking Methods

- `get_company_events(company: str, event_types: Optional[List[str]] = None, start_date: Optional[datetime] = None) -> List[Dict]`
  - Fetches company events (earnings, regulatory filings, etc.)
  - Supports filtering by event type and date
  - Returns list of event dictionaries

## Error Handling

The client includes comprehensive error handling:

```python
try:
    with BloombergClient(config) as client:
        articles = client.fetch_news_articles(...)
except Exception as e:
    logger.error(f"Bloomberg API error: {str(e)}")
```

## Testing

Unit tests are available in `tests/data_ingestion/test_bloomberg_client.py`:

```bash
pytest tests/data_ingestion/test_bloomberg_client.py
```

## Common Issues

1. Connection Issues
   - Ensure Bloomberg Terminal is running
   - Verify network connectivity
   - Check authentication credentials

2. Rate Limiting
   - Monitor request limits
   - Implement retry logic for failed requests
   - Use appropriate delay between requests

3. Data Quality
   - Validate returned data
   - Handle missing fields gracefully
   - Monitor for schema changes
