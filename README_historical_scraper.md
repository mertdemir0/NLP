# Historical News Scraper

A robust web scraper for collecting historical news articles from financial news sources without using their official APIs.

## Features

- Scrapes articles from multiple sources:
  - Bloomberg
  - Reuters
  - Financial Times
- Supports historical date-based searches
- Uses Selenium for browser automation to handle JavaScript-heavy sites
- Implements advanced techniques to avoid detection
- Extracts full article content using multiple methods for robustness
- Saves results in both JSON and CSV formats
- Parallel processing for faster scraping

## Requirements

- Python 3.8+
- Chrome browser installed
- Required Python packages (see requirements.txt)

## Installation

1. Make sure you have Python 3.8+ installed
2. Install Chrome browser if not already installed
3. Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the scraper with a search query:

```bash
python run_historical_scraper.py --query "nuclear energy"
```

This will search for articles about "nuclear energy" from the last 30 days.

### Advanced Usage

Specify a date range:

```bash
python run_historical_scraper.py --query "climate change" --start-date 2023-01-01 --end-date 2023-12-31
```

Skip content extraction (faster, but only gets metadata):

```bash
python run_historical_scraper.py --query "inflation" --no-content
```

Increase parallel workers for faster scraping (use with caution):

```bash
python run_historical_scraper.py --query "stock market" --workers 5
```

Specify a custom output directory:

```bash
python run_historical_scraper.py --query "bitcoin" --output-dir data/crypto_news
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--query` | Search query (e.g., "nuclear energy") | (Required) |
| `--start-date` | Start date in YYYY-MM-DD format | 30 days ago |
| `--end-date` | End date in YYYY-MM-DD format | Today |
| `--headless` | Run browser in headless mode | True |
| `--no-content` | Skip fetching article content | False |
| `--workers` | Number of parallel workers | 3 |
| `--output-dir` | Directory to store scraped data | data/historical_news |

## Output

The scraper saves the results in two formats:

1. **JSON**: Complete data with all fields
2. **CSV**: Tabular format for easy analysis

Output files are named with a timestamp, e.g., `articles_20230101_120000.json`.

## How It Works

1. The scraper uses Selenium to automate a Chrome browser
2. It navigates to the search pages of each news source
3. It searches for the specified query within the date range
4. It extracts article URLs, titles, and dates from search results
5. It fetches the full content of each article using multiple methods
6. It saves the results in both JSON and CSV formats

## Avoiding Detection

The scraper implements several techniques to avoid detection:

- Random delays between requests
- Rotating user agents
- Disabling WebDriver flags
- Setting a realistic window size
- Adding random mouse movements and scrolling

## Limitations

- News sites may change their HTML structure, requiring updates to the selectors
- Some sites may implement stronger anti-scraping measures
- Rate limiting may occur if too many requests are made too quickly
- Some articles may be behind paywalls and inaccessible

## Legal Considerations

Web scraping may be against the terms of service of some websites. This tool is provided for educational purposes only. Always:

1. Check the website's robots.txt file
2. Review the terms of service
3. Implement reasonable rate limiting
4. Only use the data for personal or research purposes

## Troubleshooting

### Common Issues

1. **Selenium errors**: Make sure Chrome is installed and up to date
2. **No results**: The site may have changed its HTML structure
3. **Blocked access**: The site may have detected the scraper
4. **Slow performance**: Reduce the number of workers or date range

### Logs

Check the `historical_scraping.log` file for detailed logs and error messages.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 