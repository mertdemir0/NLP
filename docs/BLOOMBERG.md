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
