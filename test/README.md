# Google Search Scraper for Bloomberg Nuclear Articles

This project is a specialized Google search scraper designed to extract Bloomberg articles about nuclear energy from 2020 to 2025 on a daily basis. The scraper performs searches with the format `site:"bloomberg.com" intitle:nuclear` with date filters for each day in the specified range.

## Features

- Daily scraping of Google search results from 2020 to 2025
- Uses [browser-use](https://github.com/browser-use/browser-use) for browser automation and AI-powered navigation
- Extraction of article titles, URLs, and snippets
- Storage of results in a SQLite database
- Export functionality to CSV
- Robust error handling and logging

## Requirements

The scraper requires:
- Python 3.11+
- Dependencies listed in `requirements.txt`
- OpenAI API key

## Installation

1. Clone this repository
2. Install the dependencies:
```
pip install -r requirements.txt
```
3. Install playwright:
```
playwright install
```

## Configuration

The scraper is configured through the `.env` file:

```
# Google Search Configuration
SITE="bloomberg.com"       # Target site to search within
KEYWORD="nuclear"          # Keyword to search for in article titles
START_DATE="2020-01-01"    # Start date for daily searches
END_DATE="2025-01-01"      # End date for daily searches
DB_PATH="sqlite:///google_search_results.db"  # Database path
MAX_PAGES=10               # Maximum pages to scrape per day

# API Keys
OPENAI_API_KEY=""         # Your OpenAI API key is required
```

## Usage

1. Add your OpenAI API key to the `.env` file
2. Run the scraper:
```
python main.py
```

The scraper will:
1. Generate daily date ranges from 2020 to 2025
2. For each day, construct a Google search query with the site and keyword filters
3. Use the browser-use AI agent to navigate Google and extract search results
4. Save the results to a SQLite database

## Exporting Data

To export the data to CSV, uncomment the line at the bottom of the script:

```python
# Uncomment to export results to CSV after scraping
export_results_to_csv()
```

## How It Works

The scraper uses the browser-use library, which combines LangChain with browser automation to create an AI agent capable of navigating web pages. For each daily search:

1. The agent navigates to Google
2. Searches with the precise query format including date filters
3. Extracts article information from search results
4. Navigates through pagination to collect results from multiple pages
5. Returns structured data that is saved to the database

## Important Notes

- This tool uses browser-use, which requires an OpenAI API key
- Be mindful of OpenAI API usage costs
- Google may still detect and restrict automated searches
- This tool should be used for educational and research purposes only
- Consider Google's Terms of Service before extensive scraping

## Database Schema

The SQLite database stores the following information for each search result:
- Title of the article
- URL of the article
- Snippet/description
- Search date (the date being searched)
- Query date (when the search was performed)
