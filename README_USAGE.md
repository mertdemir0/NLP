# Google Search Scraper Usage Guide

This guide provides instructions on how to use the Google Search Scraper tools in this project.

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements_google_scraper.txt
```

2. Make sure you have Chrome installed if you plan to use the Selenium method.

## Basic Usage

### Simple Example

The simplest way to use the scraper is with the basic example script:

```bash
python google_search_example.py
```

This will run several examples demonstrating different features of the scraper.

### Command Line Interface

For more control, use the CLI tool:

```bash
python google_search_cli.py "your search query"
```

#### CLI Options

```bash
python google_search_cli.py --help
```

Common options:
- `--results` or `-r`: Number of results to retrieve (default: 10)
- `--language` or `-l`: Language code (default: en)
- `--country` or `-c`: Country code (default: us)
- `--method` or `-m`: Scraping method (requests or selenium)
- `--output` or `-o`: Output file path
- `--format` or `-f`: Output format (json, csv, or txt)

Example with options:
```bash
python google_search_cli.py "python tutorial" --results 20 --language en --country us --method selenium --format csv --output python_tutorials.csv
```

## Advanced Usage: Keyword Research Tool

The advanced example provides a keyword research tool that can scrape multiple keywords and analyze the results:

```bash
python google_search_advanced_example.py --keywords "python web scraping" "beautiful soup tutorial"
```

Or use a file with keywords:

```bash
python google_search_advanced_example.py --file sample_keywords.txt
```

### Advanced Options

```bash
python google_search_advanced_example.py --help
```

Key options:
- `--keywords` or `-k`: List of keywords to search for
- `--file` or `-f`: File containing keywords (one per line)
- `--output` or `-o`: Output directory for results
- `--selenium` or `-s`: Use Selenium for scraping
- `--results` or `-r`: Number of results per keyword
- `--min-delay` and `--max-delay`: Delay between requests (in seconds)

## Programmatic Usage

You can also use the scraper in your own Python code:

```python
from google_search_scraper import GoogleSearchScraper

# Create a scraper instance
with GoogleSearchScraper(method="requests") as scraper:
    # Perform a search
    results = scraper.search("python tutorial", num_results=10)
    
    # Process the results
    for result in results:
        print(f"Title: {result.title}")
        print(f"URL: {result.url}")
        print(f"Snippet: {result.snippet}")
        print()
```

### Scraper Configuration Options

When creating a `GoogleSearchScraper` instance, you can customize its behavior with these parameters:

- `method`: Scraping method ("requests" or "selenium")
- `headless`: Whether to run Selenium in headless mode (default: True)
- `proxy`: Proxy server to use (e.g., "http://user:pass@host:port")
- `timeout`: Request timeout in seconds
- `max_retries`: Maximum number of retries for failed requests
- `retry_delay`: Delay between retries in seconds
- `random_delay`: Whether to use random delays between requests
- `user_agent`: Custom User-Agent string
- `cache_dir`: Directory to cache results
- `verbose`: Whether to print verbose output

### Search Method Options

The `search` method accepts these parameters:

- `query`: The search query
- `num_results`: Number of results to retrieve
- `language`: Language code (e.g., "en", "fr", "de")
- `country`: Country code (e.g., "us", "uk", "ca")
- `page`: Page number to scrape
- `safe_search`: Whether to enable safe search
- `time_period`: Time period filter (e.g., "d" for past day, "w" for past week)
- `site_search`: Limit search to a specific site

## Best Practices

1. **Respect Rate Limits**: Add delays between requests to avoid being blocked.
2. **Use Caching**: Enable caching to avoid redundant requests.
3. **Rotate User Agents**: Use different user agents to avoid detection.
4. **Consider Using Proxies**: Rotate proxies for large-scale scraping.
5. **Handle Errors Gracefully**: Implement proper error handling and retries.
6. **Be Ethical**: Respect robots.txt and website terms of service.

## Troubleshooting

### Common Issues

1. **Getting Blocked**: If you're being blocked, try:
   - Increasing the delay between requests
   - Using a proxy
   - Switching to the Selenium method
   - Rotating user agents

2. **Selenium Issues**:
   - Make sure Chrome is installed
   - Try updating the ChromeDriver
   - Check if you need to disable headless mode

3. **Empty Results**:
   - Google might be serving a CAPTCHA
   - Try using a different IP address
   - Check if your query is valid

## Legal Considerations

Web scraping may be subject to legal restrictions. Always:
- Review and respect the website's Terms of Service
- Check the robots.txt file
- Consider the copyright status of the data
- Use the data responsibly and ethically

## Advanced Features

### Custom Result Parsing

You can extend the `GoogleSearchScraper` class to customize how results are parsed:

```python
from google_search_scraper import GoogleSearchScraper

class CustomScraper(GoogleSearchScraper):
    def _parse_html(self, html):
        # Custom parsing logic
        results = super()._parse_html(html)
        # Additional processing
        return results
```

### Asynchronous Scraping

For large-scale scraping, consider implementing an asynchronous version using `aiohttp`:

```python
import asyncio
import aiohttp
from google_search_scraper import GoogleSearchResult

async def scrape_keyword(session, keyword):
    # Implement async scraping logic
    pass

async def scrape_keywords(keywords):
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_keyword(session, keyword) for keyword in keywords]
        return await asyncio.gather(*tasks)
``` 