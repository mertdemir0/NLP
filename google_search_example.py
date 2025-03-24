#!/usr/bin/env python3
"""
Google Search Scraper Example Usage

This script demonstrates how to use the GoogleSearchScraper class for various common use cases.
"""

import os
import json
from google_search_scraper import GoogleSearchScraper, GoogleSearchResult

def basic_search_example():
    """Basic search example using the default settings (requests method)"""
    print("\n=== Basic Search Example ===")
    
    # Create a scraper instance with default settings
    with GoogleSearchScraper() as scraper:
        # Perform a simple search
        results = scraper.search("python programming tutorial")
        
        # Print the results
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title}")
            print(f"   URL: {result.url}")
            print(f"   Snippet: {result.snippet[:100]}..." if result.snippet else "   No snippet")
            print()

def selenium_search_example():
    """Example using Selenium for JavaScript-heavy pages"""
    print("\n=== Selenium Search Example ===")
    
    # Create a scraper instance using Selenium
    with GoogleSearchScraper(method="selenium", headless=True) as scraper:
        # Perform a search
        results = scraper.search("machine learning frameworks", num_results=5)
        
        # Print the results
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title}")
            print(f"   URL: {result.url}")
            print()

def advanced_search_options():
    """Example demonstrating advanced search options"""
    print("\n=== Advanced Search Options Example ===")
    
    with GoogleSearchScraper() as scraper:
        # Search with time period filter (past year)
        print("Results from the past year:")
        results = scraper.search(
            "artificial intelligence news", 
            num_results=3,
            time_period="y"  # y = past year
        )
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title}")
        
        print("\nResults from a specific site:")
        # Site-specific search
        results = scraper.search(
            "data science", 
            num_results=3,
            site_search="github.com"
        )
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title}")

def save_results_example():
    """Example demonstrating how to save results to different formats"""
    print("\n=== Save Results Example ===")
    
    with GoogleSearchScraper(cache_dir="./cache") as scraper:
        # Save results to JSON
        json_file = scraper.search_and_save(
            "web scraping tools",
            output_file="web_scraping_results.json",
            num_results=10
        )
        print(f"Results saved to {json_file}")
        
        # Save results to CSV
        csv_file = scraper.search_and_save(
            "web scraping tools",
            output_file="web_scraping_results.csv",
            num_results=10,
            output_format="csv"
        )
        print(f"Results saved to {csv_file}")

def proxy_example():
    """Example demonstrating how to use a proxy (if available)"""
    print("\n=== Proxy Example ===")
    
    # Replace with your proxy if you have one
    proxy = os.environ.get("HTTP_PROXY")
    
    if proxy:
        with GoogleSearchScraper(proxy=proxy) as scraper:
            results = scraper.search("what is my ip", num_results=3)
            
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.title}")
    else:
        print("No proxy configured. Set the HTTP_PROXY environment variable to use this example.")

def main():
    """Run all examples"""
    print("Google Search Scraper Examples")
    print("=============================")
    
    # Run examples
    basic_search_example()
    selenium_search_example()
    advanced_search_options()
    save_results_example()
    proxy_example()
    
    print("\nAll examples completed!")

if __name__ == "__main__":
    main() 