import asyncio
import json
import os
from urllib.parse import quote_plus
from datetime import datetime
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

class GoogleSearchScraper:
    def __init__(self, headless=True, cache=True):
        """
        Initialize the Google Search Scraper
        
        Args:
            headless (bool): Whether to run the browser in headless mode
            cache (bool): Whether to use caching for requests
        """
        self.browser_config = BrowserConfig(
            headless=headless,
            viewport_width=1920,
            viewport_height=1080,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=True,
            # Use a modern browser
            browser_type="chromium",
        )
        
        self.crawler_config = CrawlerRunConfig(
            bypass_cache=not cache,
            timeout=60000,  # 60 seconds timeout
            wait_for_selector=".g",  # Wait for search results to load
        )
    # TODO: integrate with local browser
    async def search(self, query, num_results=10, language="en", country="us"):
        """
        Perform a Google search and extract results
        
        Args:
            query (str): The search query
            num_results (int): Number of results to extract
            language (str): Language code for search
            country (str): Country code for search
            
        Returns:
            list: List of search results with title, url, and snippet
        """
        # Encode the query for URL
        encoded_query = quote_plus(query)
        
        # Construct Google search URL
        url = f"https://www.google.com/search?q={encoded_query}&hl={language}&gl={country}&num={num_results}"
        
        # Create an instance of AsyncWebCrawler
        async with AsyncWebCrawler(
            browser_config=self.browser_config,
            crawler_config=self.crawler_config,
            verbose=True
        ) as crawler:
            # Run the crawler on the Google search URL
            result = await crawler.arun(url=url)
            
            # Extract search results using CSS selectors
            search_results = []
            
            # Use BeautifulSoup to parse the HTML
            soup = result.soup
            
            # Find all search result containers
            result_containers = soup.select(".g")
            
            for container in result_containers:
                try:
                    # Extract title
                    title_element = container.select_one("h3")
                    title = title_element.text if title_element else "No title found"
                    
                    # Extract URL
                    link_element = container.select_one("a")
                    url = link_element.get("href") if link_element else "No URL found"
                    
                    # Extract snippet
                    snippet_element = container.select_one(".VwiC3b")
                    snippet = snippet_element.text if snippet_element else "No snippet found"
                    
                    # Add to results
                    search_results.append({
                        "title": title,
                        "url": url,
                        "snippet": snippet
                    })
                except Exception as e:
                    print(f"Error extracting result: {e}")
            
            return search_results
    
    async def search_and_save(self, query, output_file=None, num_results=10, language="en", country="us"):
        """
        Perform a Google search and save results to a JSON file
        
        Args:
            query (str): The search query
            output_file (str): Path to save the results (if None, generates a filename)
            num_results (int): Number of results to extract
            language (str): Language code for search
            country (str): Country code for search
            
        Returns:
            str: Path to the saved file
        """
        # Get search results
        results = await self.search(query, num_results, language, country)
        
        # Generate output filename if not provided
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_query = query.replace(" ", "_")[:30]  # Limit length for filename
            output_file = f"google_search_{safe_query}_{timestamp}.json"
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
        
        # Save results to JSON file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "num_results": len(results),
                "results": results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Search results saved to {output_file}")
        return output_file

async def main():
    # Create an instance of GoogleSearchScraper
    scraper = GoogleSearchScraper(headless=True, cache=True)
    
    # Example search query
    query = "artificial intelligence news"
    
    # Search and save results
    output_file = await scraper.search_and_save(
        query=query,
        num_results=10,
        language="en",
        country="us"
    )
    
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(main()) 