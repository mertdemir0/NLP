# Google Search Scraper

A powerful and flexible Google search scraper built with Crawl4AI. This tool allows you to extract search results from Google and save them in JSON format.

## Features

- Extract search results including titles, URLs, and snippets
- Configurable number of results
- Language and country-specific searches
- Stealth mode to avoid detection
- Caching for faster repeated searches
- Command-line interface for easy use

## Installation

1. Create a virtual environment:
```bash
python -m venv google_scraper_env
source google_scraper_env/bin/activate  # On Windows: google_scraper_env\Scripts\activate
```

2. Install the required packages:
```bash
pip install crawl4ai
```

3. Install browser dependencies:
```bash
python -m playwright install --with-deps chromium
```

## Usage

### Command-line Interface

The easiest way to use the scraper is through the command-line interface:

```bash
python google_search_cli.py "your search query" --results 20 --language en --country us
```

#### Options:

- `query`: The search query (required)
- `--results`, `-r`: Number of results to retrieve (default: 10)
- `--language`, `-l`: Language code for search (default: en)
- `--country`, `-c`: Country code for search (default: us)
- `--output`, `-o`: Output file path (default: auto-generated)
- `--no-cache`: Disable caching of requests
- `--no-headless`: Disable headless mode (show browser)

### Python API

You can also use the scraper in your Python code:

```python
import asyncio
from google_search_scraper import GoogleSearchScraper

async def main():
    # Create an instance of GoogleSearchScraper
    scraper = GoogleSearchScraper(headless=True, cache=True)
    
    # Search and save results
    output_file = await scraper.search_and_save(
        query="artificial intelligence news",
        num_results=10,
        language="en",
        country="us"
    )
    
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Output Format

The scraper saves results in JSON format with the following structure:

```json
{
  "query": "your search query",
  "timestamp": "2024-11-06T12:34:56.789012",
  "num_results": 10,
  "results": [
    {
      "title": "Result Title",
      "url": "https://example.com/page",
      "snippet": "This is a snippet of the search result..."
    },
    ...
  ]
}
```

## Notes

- Google may block automated requests if too many are made in a short period. Use responsibly.
- The scraper uses stealth mode to avoid detection, but it's not guaranteed to work in all cases.
- The CSS selectors used to extract results may need to be updated if Google changes its HTML structure.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Crawl4AI](https://github.com/unclecode/crawl4ai) - The powerful web crawler used in this project 