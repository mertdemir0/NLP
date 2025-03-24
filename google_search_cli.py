#!/usr/bin/env python3
import argparse
import sys
import os
import json
from typing import Dict, Any

# Add the current directory to the path to import the GoogleSearchScraper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from google_search_scraper import GoogleSearchScraper

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Google Search Scraper CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Required arguments
    parser.add_argument(
        "query", 
        help="The search query to use"
    )
    
    # Search parameters
    search_group = parser.add_argument_group("Search Parameters")
    search_group.add_argument(
        "--results", "-r", 
        type=int, 
        default=10, 
        help="Number of results to retrieve"
    )
    search_group.add_argument(
        "--language", "-l", 
        default="en", 
        help="Language code for search (e.g., en, fr, de)"
    )
    search_group.add_argument(
        "--country", "-c", 
        default="us", 
        help="Country code for search (e.g., us, uk, ca)"
    )
    search_group.add_argument(
        "--page", "-p", 
        type=int, 
        default=1, 
        help="Page number to scrape (1-based)"
    )
    search_group.add_argument(
        "--no-safe-search", 
        action="store_true", 
        help="Disable safe search"
    )
    search_group.add_argument(
        "--time-period", "-t", 
        choices=["day", "week", "month", "year"], 
        help="Time period for results"
    )
    search_group.add_argument(
        "--site", "-s", 
        help="Limit search to specific site (e.g., example.com)"
    )
    
    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--output", "-o", 
        help="Output file path (default: auto-generated)"
    )
    output_group.add_argument(
        "--format", "-f", 
        choices=["json", "csv", "txt"], 
        default="json", 
        help="Output format"
    )
    output_group.add_argument(
        "--pretty", 
        action="store_true", 
        help="Pretty print JSON output"
    )
    output_group.add_argument(
        "--print", 
        action="store_true", 
        help="Print results to console"
    )
    
    # Scraper options
    scraper_group = parser.add_argument_group("Scraper Options")
    scraper_group.add_argument(
        "--method", "-m", 
        choices=["requests", "selenium"], 
        default="requests", 
        help="Scraping method to use"
    )
    scraper_group.add_argument(
        "--no-headless", 
        action="store_true", 
        help="Disable headless mode (show browser)"
    )
    scraper_group.add_argument(
        "--proxy", 
        help="Proxy to use (format: http://user:pass@host:port)"
    )
    scraper_group.add_argument(
        "--timeout", 
        type=int, 
        default=30, 
        help="Request timeout in seconds"
    )
    scraper_group.add_argument(
        "--retries", 
        type=int, 
        default=3, 
        help="Maximum number of retries for failed requests"
    )
    scraper_group.add_argument(
        "--delay", 
        type=int, 
        default=5, 
        help="Delay between retries in seconds"
    )
    scraper_group.add_argument(
        "--no-random-delay", 
        action="store_true", 
        help="Disable random delay between requests"
    )
    scraper_group.add_argument(
        "--user-agent", 
        help="Custom user agent string"
    )
    scraper_group.add_argument(
        "--cache-dir", 
        default="cache", 
        help="Directory to cache results (empty to disable)"
    )
    scraper_group.add_argument(
        "--verbose", "-v", 
        action="store_true", 
        help="Enable verbose output"
    )
    
    return parser.parse_args()

def save_results_as_csv(results, output_file, query):
    """Save results to a CSV file"""
    import csv
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["position", "title", "url", "displayed_url", "snippet", "featured", "is_ad", "is_video", "is_news"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            result_dict = result.to_dict()
            # Only include the main fields in CSV
            writer.writerow({
                "position": result_dict["position"],
                "title": result_dict["title"],
                "url": result_dict["url"],
                "displayed_url": result_dict["displayed_url"],
                "snippet": result_dict["snippet"],
                "featured": result_dict["featured"],
                "is_ad": result_dict["is_ad"],
                "is_video": result_dict["is_video"],
                "is_news": result_dict["is_news"]
            })
    
    return output_file

def save_results_as_txt(results, output_file, query):
    """Save results to a text file"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Search Query: {query}\n")
        f.write(f"Results: {len(results)}\n\n")
        
        for i, result in enumerate(results, 1):
            result_dict = result.to_dict()
            f.write(f"Result #{i} {'(Featured)' if result_dict['featured'] else ''}\n")
            f.write(f"Title: {result_dict['title']}\n")
            f.write(f"URL: {result_dict['url']}\n")
            f.write(f"Snippet: {result_dict['snippet']}\n")
            f.write("-" * 80 + "\n\n")
    
    return output_file

def print_results(results, query):
    """Print results to console"""
    print(f"\nSearch Query: {query}")
    print(f"Results: {len(results)}\n")
    
    for i, result in enumerate(results, 1):
        result_dict = result.to_dict()
        print(f"Result #{i} {'(Featured)' if result_dict['featured'] else ''}")
        print(f"Title: {result_dict['title']}")
        print(f"URL: {result_dict['url']}")
        print(f"Snippet: {result_dict['snippet']}")
        print("-" * 80 + "\n")

def main():
    """Main function"""
    # Parse arguments
    args = parse_arguments()
    
    # Determine cache directory
    cache_dir = args.cache_dir if args.cache_dir else None
    
    # Create scraper instance
    scraper = GoogleSearchScraper(
        method=args.method,
        headless=not args.no_headless,
        proxy=args.proxy,
        timeout=args.timeout,
        max_retries=args.retries,
        retry_delay=args.delay,
        random_delay=not args.no_random_delay,
        user_agent=args.user_agent,
        cache_dir=cache_dir,
        verbose=args.verbose
    )
    
    try:
        # Perform search
        results = scraper.search(
            query=args.query,
            num_results=args.results,
            language=args.language,
            country=args.country,
            page=args.page,
            safe_search=not args.no_safe_search,
            time_period=args.time_period,
            site_search=args.site
        )
        
        # Generate output filename if not provided
        if args.output is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_query = "".join(c if c.isalnum() else "_" for c in args.query)[:30]
            
            if args.format == "json":
                args.output = f"google_search_{safe_query}_{timestamp}.json"
            elif args.format == "csv":
                args.output = f"google_search_{safe_query}_{timestamp}.csv"
            else:  # txt
                args.output = f"google_search_{safe_query}_{timestamp}.txt"
        
        # Save results in the specified format
        if args.format == "json":
            # Save as JSON
            with open(args.output, "w", encoding="utf-8") as f:
                json_data = {
                    "query": args.query,
                    "timestamp": datetime.now().isoformat(),
                    "num_results": len(results),
                    "results": [result.to_dict() for result in results]
                }
                
                if args.pretty:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(json_data, f, ensure_ascii=False)
        elif args.format == "csv":
            # Save as CSV
            save_results_as_csv(results, args.output, args.query)
        else:  # txt
            # Save as text
            save_results_as_txt(results, args.output, args.query)
        
        # Print results if requested
        if args.print:
            print_results(results, args.query)
        
        print(f"\nSearch completed successfully!")
        print(f"Results saved to: {args.output}")
        
    except Exception as e:
        print(f"Error during search: {e}")
        return 1
    finally:
        # Always close the scraper to release resources
        scraper.close()
    
    return 0

if __name__ == "__main__":
    # Run the main function
    exit_code = main()
    sys.exit(exit_code) 