"""Configuration file for API credentials and settings."""

# Bloomberg API credentials
BLOOMBERG_API = {
    'username': '',  # Your Bloomberg username
    'password': '',  # Your Bloomberg password
    'api_key': '',  # Your Bloomberg API key
    'base_url': 'https://bba.bloomberg.com/api/v1'
}

# Scraper settings
SCRAPER_CONFIG = {
    'max_articles_per_source': 50,
    'request_timeout': 30,
    'retry_attempts': 3,
    'retry_delay': 5
}
