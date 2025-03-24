#!/usr/bin/env python3
"""
Google Search Scraper Advanced Example

This script demonstrates a more advanced use case for the GoogleSearchScraper:
- Scraping search results for multiple keywords
- Saving the results to a structured format
- Performing basic analysis on the collected data
- Implementing rate limiting and error handling
"""

import os
import json
import time
import random
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from collections import Counter

import pandas as pd
from tqdm import tqdm

from google_search_scraper import GoogleSearchScraper, GoogleSearchResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("keyword_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("KeywordScraper")

class KeywordResearchScraper:
    """Class for scraping and analyzing Google search results for multiple keywords"""
    
    def __init__(
        self,
        output_dir: str = "keyword_research",
        use_selenium: bool = False,
        num_results: int = 10,
        language: str = "en",
        country: str = "us",
        cache_results: bool = True,
        min_delay: int = 5,
        max_delay: int = 15,
        max_retries: int = 3
    ):
        """
        Initialize the keyword research scraper
        
        Args:
            output_dir: Directory to save results
            use_selenium: Whether to use Selenium for scraping
            num_results: Number of results to retrieve per keyword
            language: Language code for search
            country: Country code for search
            cache_results: Whether to cache results
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.output_dir = output_dir
        self.use_selenium = use_selenium
        self.num_results = num_results
        self.language = language
        self.country = country
        self.cache_results = cache_results
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize the scraper
        self.scraper = GoogleSearchScraper(
            method="selenium" if use_selenium else "requests",
            headless=True,
            max_retries=max_retries,
            random_delay=True,
            cache_dir=os.path.join(output_dir, "cache") if cache_results else None,
            verbose=True
        )
        
        # Store results
        self.results: Dict[str, List[GoogleSearchResult]] = {}
        
    def scrape_keywords(self, keywords: List[str]) -> Dict[str, List[GoogleSearchResult]]:
        """
        Scrape search results for a list of keywords
        
        Args:
            keywords: List of keywords to scrape
            
        Returns:
            Dictionary mapping keywords to their search results
        """
        logger.info(f"Starting to scrape {len(keywords)} keywords")
        
        for keyword in tqdm(keywords, desc="Scraping keywords"):
            try:
                # Add random delay to avoid detection
                delay = random.uniform(self.min_delay, self.max_delay)
                logger.info(f"Scraping keyword: '{keyword}' (waiting {delay:.2f}s)")
                time.sleep(delay)
                
                # Search for the keyword
                results = self.scraper.search(
                    query=keyword,
                    num_results=self.num_results,
                    language=self.language,
                    country=self.country
                )
                
                # Store the results
                self.results[keyword] = results
                
                # Save individual keyword results
                self._save_keyword_results(keyword, results)
                
            except Exception as e:
                logger.error(f"Error scraping keyword '{keyword}': {str(e)}")
        
        # Save all results
        self._save_all_results()
        
        return self.results
    
    def _save_keyword_results(self, keyword: str, results: List[GoogleSearchResult]) -> None:
        """Save results for a single keyword"""
        # Create a safe filename from the keyword
        safe_keyword = "".join(c if c.isalnum() else "_" for c in keyword).lower()
        
        # Save as JSON
        json_path = os.path.join(self.output_dir, f"{safe_keyword}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "keyword": keyword,
                    "timestamp": datetime.now().isoformat(),
                    "results": [r.to_dict() for r in results]
                },
                f,
                indent=2,
                ensure_ascii=False
            )
        
        logger.info(f"Saved results for '{keyword}' to {json_path}")
    
    def _save_all_results(self) -> None:
        """Save all results to a single file"""
        if not self.results:
            logger.warning("No results to save")
            return
        
        # Save as JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(self.output_dir, f"all_keywords_{timestamp}.json")
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "keywords": list(self.results.keys()),
                    "results": {k: [r.to_dict() for r in v] for k, v in self.results.items()}
                },
                f,
                indent=2,
                ensure_ascii=False
            )
        
        logger.info(f"Saved all results to {json_path}")
        
        # Save as CSV
        csv_path = os.path.join(self.output_dir, f"all_keywords_{timestamp}.csv")
        
        # Flatten the results for CSV
        flattened_results = []
        for keyword, results_list in self.results.items():
            for position, result in enumerate(results_list, 1):
                flattened_results.append({
                    "keyword": keyword,
                    "position": position,
                    "title": result.title,
                    "url": result.url,
                    "displayed_url": result.displayed_url,
                    "snippet": result.snippet,
                    "featured": result.featured,
                    "is_ad": result.is_ad,
                    "is_video": result.is_video,
                    "is_news": result.is_news
                })
        
        # Convert to DataFrame and save
        df = pd.DataFrame(flattened_results)
        df.to_csv(csv_path, index=False, encoding="utf-8")
        
        logger.info(f"Saved all results as CSV to {csv_path}")
    
    def analyze_results(self) -> Dict[str, Any]:
        """
        Perform basic analysis on the collected search results
        
        Returns:
            Dictionary containing analysis results
        """
        if not self.results:
            logger.warning("No results to analyze")
            return {}
        
        logger.info("Analyzing search results")
        
        # Extract all domains
        all_domains = []
        for keyword, results in self.results.items():
            for result in results:
                if result.url:
                    domain = urlparse(result.url).netloc
                    all_domains.append(domain)
        
        # Count domain frequencies
        domain_counts = Counter(all_domains)
        top_domains = domain_counts.most_common(10)
        
        # Count featured snippets
        featured_snippets = sum(
            1 for results in self.results.values() 
            for result in results if result.featured
        )
        
        # Count ads
        ads = sum(
            1 for results in self.results.values() 
            for result in results if result.is_ad
        )
        
        # Prepare analysis results
        analysis = {
            "total_keywords": len(self.results),
            "total_results": sum(len(results) for results in self.results.values()),
            "top_domains": top_domains,
            "featured_snippets": featured_snippets,
            "ads": ads
        }
        
        # Save analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_path = os.path.join(self.output_dir, f"analysis_{timestamp}.json")
        
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2)
        
        logger.info(f"Saved analysis to {analysis_path}")
        
        return analysis
    
    def close(self):
        """Close the scraper"""
        self.scraper.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Google Search Keyword Research Tool")
    
    parser.add_argument(
        "--keywords", "-k",
        nargs="+",
        help="List of keywords to search for"
    )
    
    parser.add_argument(
        "--file", "-f",
        help="File containing keywords (one per line)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="keyword_research",
        help="Output directory for results"
    )
    
    parser.add_argument(
        "--selenium", "-s",
        action="store_true",
        help="Use Selenium for scraping (slower but better for complex pages)"
    )
    
    parser.add_argument(
        "--results", "-r",
        type=int,
        default=10,
        help="Number of results to retrieve per keyword"
    )
    
    parser.add_argument(
        "--language", "-l",
        default="en",
        help="Language code for search"
    )
    
    parser.add_argument(
        "--country", "-c",
        default="us",
        help="Country code for search"
    )
    
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching of results"
    )
    
    parser.add_argument(
        "--min-delay",
        type=int,
        default=5,
        help="Minimum delay between requests in seconds"
    )
    
    parser.add_argument(
        "--max-delay",
        type=int,
        default=15,
        help="Maximum delay between requests in seconds"
    )
    
    args = parser.parse_args()
    
    # Get keywords
    keywords = []
    
    if args.keywords:
        keywords.extend(args.keywords)
    
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                file_keywords = [line.strip() for line in f if line.strip()]
                keywords.extend(file_keywords)
        except Exception as e:
            logger.error(f"Error reading keywords file: {str(e)}")
    
    if not keywords:
        logger.error("No keywords provided. Use --keywords or --file")
        parser.print_help()
        return
    
    # Remove duplicates while preserving order
    keywords = list(dict.fromkeys(keywords))
    
    logger.info(f"Loaded {len(keywords)} keywords")
    
    # Create and run the scraper
    with KeywordResearchScraper(
        output_dir=args.output,
        use_selenium=args.selenium,
        num_results=args.results,
        language=args.language,
        country=args.country,
        cache_results=not args.no_cache,
        min_delay=args.min_delay,
        max_delay=args.max_delay
    ) as scraper:
        # Scrape keywords
        results = scraper.scrape_keywords(keywords)
        
        # Analyze results
        analysis = scraper.analyze_results()
        
        # Print summary
        print("\nScraping Summary:")
        print(f"Total keywords scraped: {len(results)}")
        print(f"Total results collected: {sum(len(r) for r in results.values())}")
        
        if analysis:
            print("\nTop domains:")
            for domain, count in analysis["top_domains"]:
                print(f"  {domain}: {count}")
            
            print(f"\nFeatured snippets: {analysis['featured_snippets']}")
            print(f"Ads: {analysis['ads']}")
        
        print(f"\nResults saved to {os.path.abspath(args.output)}")

if __name__ == "__main__":
    main() 