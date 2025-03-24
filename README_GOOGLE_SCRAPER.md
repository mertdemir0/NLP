# Google Search Scraper

A powerful and flexible Python tool for scraping Google search results with multiple methods and options.

## Features

- **Multiple Scraping Methods**: Choose between `requests` (faster, simpler) and `selenium` (better for JavaScript-heavy pages)
- **Comprehensive Results**: Extracts titles, URLs, snippets, and more from search results
- **Result Types**: Identifies organic results, featured snippets, ads, videos, and news
- **Pagination Support**: Scrape multiple pages of search results
- **Advanced Search Options**: Time filtering, site-specific search, safe search toggle
- **Multiple Output Formats**: Save results as JSON, CSV, or plain text
- **Caching**: Optional caching to avoid redundant requests
- **Proxy Support**: Use proxies to avoid rate limiting and IP blocking
- **Robust Error Handling**: Automatic retries with exponential backoff
- **Anti-Detection Measures**: Random delays, custom user agents, and browser fingerprint masking

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Setup

1. Clone this repository or download the source code:

```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python google_search_cli.py "your search query"
```

This will perform a basic search and save the results to a JSON file with an auto-generated name.

### Command Line Options

#### Search Parameters

```bash
# Search for "python web scraping" and get 20 results
python google_search_cli.py "python web scraping" --results 20

# Search in French from France
python google_search_cli.py "python web scraping" --language fr --country fr

# Get results from the second page
python google_search_cli.py "python web scraping" --page 2

# Disable safe search
python google_search_cli.py "python web scraping" --no-safe-search

# Get results from the past month
python google_search_cli.py "python web scraping" --time-period month

# Search only within a specific site
python google_search_cli.py "web scraping" --site python.org
```

#### Output Options

```bash
# Save results to a specific file
python google_search_cli.py "python web scraping" --output results.json

# Save results as CSV
python google_search_cli.py "python web scraping" --format csv

# Save results as plain text
python google_search_cli.py "python web scraping" --format txt

# Pretty print JSON output
python google_search_cli.py "python web scraping" --pretty

# Print results to console
python google_search_cli.py "python web scraping" --print
```

#### Scraper Options

```bash
# Use Selenium for JavaScript-heavy pages
python google_search_cli.py "python web scraping" --method selenium

# Show browser window (Selenium only)
python google_search_cli.py "python web scraping" --method selenium --no-headless

# Use a proxy
python google_search_cli.py "python web scraping" --proxy http://user:pass@host:port

# Set custom timeout, retries, and delay
python google_search_cli.py "python web scraping" --timeout 60 --retries 5 --delay 10

# Disable random delay
python google_search_cli.py "python web scraping" --no-random-delay

# Set custom user agent
python google_search_cli.py "python web scraping" --user-agent "Mozilla/5.0 ..."

# Set custom cache directory
python google_search_cli.py "python web scraping" --cache-dir my_cache

# Disable caching
python google_search_cli.py "python web scraping" --cache-dir ""

# Enable verbose output
python google_search_cli.py "python web scraping" --verbose
```

### Using as a Library

You can also use the `GoogleSearchScraper` class directly in your Python code:

```python
from google_search_scraper import GoogleSearchScraper

# Create a scraper instance
scraper = GoogleSearchScraper(
    method="requests",  # or "selenium"
    headless=True,
    random_delay=True,
    cache_dir="cache"
)

try:
    # Perform a search
    results = scraper.search(
        query="python web scraping",
        num_results=10,
        language="en",
        country="us",
        time_period="month"
    )
    
    # Process the results
    for result in results:
        print(f"Title: {result.title}")
        print(f"URL: {result.url}")
        print(f"Snippet: {result.snippet}")
        print("-" * 50)
        
    # Or save the results to a file
    output_file = scraper.search_and_save(
        query="python web scraping",
        output_file="results.json",
        num_results=10
    )
    print(f"Results saved to {output_file}")
    
finally:
    # Always close the scraper to release resources
    scraper.close()
```

## Best Practices

### Avoiding Detection and Blocking

Google actively tries to detect and block scrapers. To minimize the risk:

1. **Use Reasonable Delays**: Don't make too many requests in a short time
2. **Rotate User Agents**: Use different user agents for different requests
3. **Use Proxies**: Rotate between multiple proxies to distribute requests
4. **Respect Robots.txt**: Check Google's robots.txt for allowed crawling
5. **Cache Results**: Use caching to avoid redundant requests
6. **Be Gentle**: Don't scrape aggressively or in a way that could impact Google's services

### Ethical Considerations

- Only scrape publicly available data
- Use the data for legitimate purposes
- Respect Google's terms of service
- Consider using Google's official APIs for production use

## Troubleshooting

### Common Issues

1. **CAPTCHA Detection**: If you see "Our systems have detected unusual traffic from your computer network" in the results, Google has detected your scraping. Try:
   - Using a proxy
   - Reducing request frequency
   - Using a different user agent
   - Switching to the Selenium method

2. **Empty Results**: If you're getting empty results:
   - Check your internet connection
   - Verify that your proxy is working (if using one)
   - Try the Selenium method instead of requests
   - Check if Google has changed its HTML structure

3. **Selenium Issues**:
   - Ensure you have the correct ChromeDriver version installed
   - Try running without headless mode to see what's happening
   - Check for any browser errors in the logs

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Use responsibly and in accordance with Google's terms of service. The authors are not responsible for any misuse or consequences thereof.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request 