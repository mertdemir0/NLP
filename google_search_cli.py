import asyncio
import argparse
import sys
import os

# Add the current directory to the path to import the GoogleSearchScraper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from google_search_scraper import GoogleSearchScraper

async def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description="Google Search Scraper CLI")
    
    # Add arguments
    parser.add_argument("query", help="The search query to use")
    parser.add_argument("--results", "-r", type=int, default=10, help="Number of results to retrieve (default: 10)")
    parser.add_argument("--language", "-l", default="en", help="Language code for search (default: en)")
    parser.add_argument("--country", "-c", default="us", help="Country code for search (default: us)")
    parser.add_argument("--output", "-o", help="Output file path (default: auto-generated)")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching of requests")
    parser.add_argument("--no-headless", action="store_true", help="Disable headless mode (show browser)")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Create scraper instance
    scraper = GoogleSearchScraper(
        headless=not args.no_headless,
        cache=not args.no_cache
    )
    
    try:
        # Search and save results
        output_file = await scraper.search_and_save(
            query=args.query,
            output_file=args.output,
            num_results=args.results,
            language=args.language,
            country=args.country
        )
        
        print(f"\nSearch completed successfully!")
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error during search: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 