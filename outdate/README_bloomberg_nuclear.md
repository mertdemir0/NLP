# Bloomberg Nuclear Articles Scraper

A specialized scraper for collecting all Bloomberg articles about nuclear energy from January 2020 to March 2025 and storing them in a SQLite database.

## Features

- Scrapes Bloomberg articles with the keyword "nuclear"
- Covers the date range from January 2020 to March 2025
- Stores articles in a SQLite database for easy querying
- Breaks the scraping task into manageable chunks by date
- Supports resuming from the last scraped date
- Implements techniques to avoid detection
- Extracts full article content
- Exports results to JSON for backup

## Requirements

- Python 3.8+
- Chrome browser installed
- Required Python packages:
  - selenium
  - beautifulsoup4
  - newspaper3k
  - fake-useragent
  - trafilatura
  - readability-lxml
  - webdriver-manager
  - pandas
  - tqdm
  - python-dateutil

## Installation

1. Make sure you have Python 3.8+ installed
2. Install Chrome browser if not already installed
3. Install the required Python packages:

```bash
pip install selenium beautifulsoup4 newspaper3k fake-useragent trafilatura readability-lxml webdriver-manager pandas tqdm python-dateutil
```

## Usage

### Basic Usage

Run the scraper with default settings:

```bash
python scrape_bloomberg_nuclear.py
```

This will scrape Bloomberg articles about "nuclear" from January 2020 to March 2025, processing 3 months at a time.

### Advanced Usage

Specify a custom date range:

```bash
python scrape_bloomberg_nuclear.py --start-date 2022-01-01 --end-date 2023-12-31
```

Change the chunk size (number of months to process at once):

```bash
python scrape_bloomberg_nuclear.py --chunk-months 1
```

Resume from the last scraped date:

```bash
python scrape_bloomberg_nuclear.py --resume
```

Specify a custom database path:

```bash
python scrape_bloomberg_nuclear.py --db-path data/custom_nuclear.db
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--start-date` | Start date in YYYY-MM-DD format | 2020-01-01 |
| `--end-date` | End date in YYYY-MM-DD format | 2025-03-31 |
| `--query` | Search query | nuclear |
| `--headless` | Run browser in headless mode | True |
| `--workers` | Number of parallel workers | 1 |
| `--chunk-months` | Number of months to scrape in each chunk | 3 |
| `--db-path` | Path to SQLite database | data/bloomberg_nuclear.db |
| `--resume` | Resume from last scraped date | False |

## Database Schema

The scraper stores articles in a SQLite database with the following schema:

### Articles Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| url | TEXT | Article URL (unique) |
| title | TEXT | Article title |
| date | TEXT | Article date from search results |
| publish_date | TEXT | Article publish date from content |
| text | TEXT | Full article text |
| summary | TEXT | Article summary |
| authors | TEXT | JSON array of authors |
| keywords | TEXT | JSON array of keywords |
| top_image | TEXT | URL of the top image |
| html_content | TEXT | HTML content of the article |
| scraped_at | TEXT | Timestamp when the article was scraped |
| created_at | TEXT | Timestamp when the record was created |

### Scraping Metadata Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| start_date | TEXT | Start date of the scraping period |
| end_date | TEXT | End date of the scraping period |
| query | TEXT | Search query |
| last_scraped_date | TEXT | Last date that was scraped |
| total_articles | INTEGER | Total number of articles scraped |
| status | TEXT | Status of the scraping process |
| created_at | TEXT | Timestamp when the record was created |
| updated_at | TEXT | Timestamp when the record was last updated |

## Querying the Database

You can query the database using SQLite tools or Python. Here's an example of how to query the database using Python:

```python
import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('data/bloomberg_nuclear.db')

# Query all articles
df = pd.read_sql_query("SELECT * FROM articles", conn)

# Query articles by date range
df_2022 = pd.read_sql_query(
    "SELECT * FROM articles WHERE date BETWEEN '2022-01-01' AND '2022-12-31'", 
    conn
)

# Query articles containing specific text
df_smr = pd.read_sql_query(
    "SELECT * FROM articles WHERE text LIKE '%small modular reactor%'", 
    conn
)

# Close the connection
conn.close()
```

## Exporting Data

The scraper automatically exports all articles to a JSON file after completion. You can also export the data manually using the `export_to_json` method of the `BloombergDB` class:

```python
from src.database.bloomberg_db import BloombergDB

# Initialize the database
db = BloombergDB()

# Export all articles to JSON
db.export_to_json('data/bloomberg_nuclear_export.json')

# Close the database connection
db.close()
```

## Troubleshooting

### Common Issues

1. **Selenium errors**: Make sure Chrome is installed and up to date
2. **No results**: The site may have changed its HTML structure
3. **Blocked access**: The site may have detected the scraper
4. **Database errors**: Check file permissions and disk space

### Logs

Check the `bloomberg_nuclear_scraping.log` file for detailed logs and error messages.

## Legal Considerations

Web scraping may be against the terms of service of some websites. This tool is provided for educational purposes only. Always:

1. Check the website's robots.txt file
2. Review the terms of service
3. Implement reasonable rate limiting
4. Only use the data for personal or research purposes

## License

This project is licensed under the MIT License - see the LICENSE file for details. 