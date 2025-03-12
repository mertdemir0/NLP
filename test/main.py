import os
import time
import asyncio
import logging
import json
from datetime import datetime, timedelta
from tqdm import tqdm
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from browser_use import Agent
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.orm import declarative_base, sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants from .env file
SITE = os.getenv("SITE")
KEYWORD = os.getenv("KEYWORD")
START_DATE = os.getenv("START_DATE")
END_DATE = os.getenv("END_DATE")
DB_PATH = os.getenv("DB_PATH")
MAX_PAGES = int(os.getenv("MAX_PAGES", 10))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Setup SQLAlchemy
Base = declarative_base()

class SearchResult(Base):
    __tablename__ = 'search_results'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    url = Column(String(1000))
    snippet = Column(Text)
    search_date = Column(String(20))
    query_date = Column(DateTime)
    
    def __repr__(self):
        return f"<SearchResult(title='{self.title}', date='{self.search_date}')>"

# Initialize database
engine = create_engine(DB_PATH)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def save_results_to_db(results, search_date):
    """Save search results to the database."""
    session = Session()
    try:
        for result in results:
            search_result = SearchResult(
                title=result["title"],
                url=result["url"],
                snippet=result["snippet"],
                search_date=search_date,
                query_date=datetime.now()
            )
            session.add(search_result)
        session.commit()
        logger.info(f"Saved {len(results)} results to the database for {search_date}")
    except Exception as e:
        session.rollback()
        logger.error(f"Error saving to database: {e}")
    finally:
        session.close()

def get_date_ranges():
    """Generate daily date ranges from START_DATE to END_DATE."""
    start = datetime.strptime(START_DATE, "%Y-%m-%d")
    end = datetime.strptime(END_DATE, "%Y-%m-%d")
    
    date_ranges = []
    current_date = start
    
    while current_date < end:
        next_date = current_date + timedelta(days=1)
        date_ranges.append((current_date, next_date))
        current_date = next_date
        
    return date_ranges

def extract_results_from_output(output_str, date_str):
    """Extract results from the agent's output string."""
    results = []
    try:
        # Look for JSON arrays in the output string
        json_start = output_str.find('[')
        json_end = output_str.rfind(']') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_text = output_str[json_start:json_end]
            try:
                parsed = json.loads(json_text)
                if isinstance(parsed, list) and len(parsed) > 0:
                    # Ensure each item has the required fields
                    for item in parsed:
                        if isinstance(item, dict) and 'title' in item and 'url' in item:
                            if 'snippet' not in item:
                                item['snippet'] = ''
                            results.append(item)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from output for {date_str}")
    except Exception as e:
        logger.error(f"Error extracting results from output: {e}")
    
    logger.info(f"Extracted {len(results)} results from output for {date_str}")
    return results

async def search_for_date(start_date, end_date):
    """Use browser-use to search Google for a specific date range."""
    # Format dates for display
    date_str = start_date.strftime("%Y-%m-%d")
    logger.info(f"Processing date range: {date_str}")
    
    # Format dates for Google search
    formatted_start = start_date.strftime("%m/%d/%Y")
    formatted_end = end_date.strftime("%m/%d/%Y")
    
    # Construct search query
    search_query = f'site:{SITE} intitle:{KEYWORD} after:{formatted_start} before:{formatted_end}'
    logger.info(f"Search query: {search_query}")
    
    # Prepare the task for the browser-use agent
    task = f"""
    1. Go to Google.com
    2. Search for this exact query: {search_query}
    3. For each result on the first {MAX_PAGES} pages of search results (navigate through pagination as needed):
       - Extract the article title
       - Extract the article URL
       - Extract the snippet text
    4. Only collect results from {SITE}
    5. At the end of your response, provide a JSON array of objects with the extracted data. Each object should have 'title', 'url', and 'snippet' fields.
    6. Format the JSON array EXACTLY like this example:
    [
      {{
        "title": "Article Title 1",
        "url": "https://www.bloomberg.com/article1",
        "snippet": "This is the snippet text for article 1"
      }},
      {{
        "title": "Article Title 2",
        "url": "https://www.bloomberg.com/article2",
        "snippet": "This is the snippet text for article 2"
      }}
    ]
    """
    
    # Initialize the language model
    llm = ChatOpenAI(
        model='gpt-4o',
        temperature=0.0,
    )
    
    # Initialize and run the agent
    agent = Agent(task=task, llm=llm)
    
    try:
        # Run the agent and get the result
        result = await agent.run()
        
        # Extract structured data from the agent's output
        if result:
            # Save the raw output to a file for debugging
            output_file = f"results_{date_str}.txt"
            with open(output_file, 'w') as f:
                f.write(str(result))
            
            # Extract the results
            if isinstance(result, str):
                results = extract_results_from_output(result, date_str)
                
                # Save to JSON file as well
                if results:
                    json_file = f"results_{date_str}.json"
                    with open(json_file, 'w') as f:
                        json.dump(results, f)
                
                return results, date_str
    except Exception as e:
        logger.error(f"Error running agent for {date_str}: {e}")
    
    return [], date_str

async def main():
    """Main async function to run the scraper."""
    logger.info("Starting Google search scraper with browser-use")
    
    try:
        # Get all date ranges to search
        date_ranges = get_date_ranges()
        logger.info(f"Generated {len(date_ranges)} daily date ranges to search")
        
        # Process each date range
        for start_date, end_date in tqdm(date_ranges, desc="Processing date ranges"):
            results, date_str = await search_for_date(start_date, end_date)
            
            # Save results to database
            if results:
                save_results_to_db(results, date_str)
            
            # Delay to avoid being blocked
            time.sleep(5)
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        logger.info("Scraper completed")

def export_results_to_csv():
    """Export all results from the database to a CSV file."""
    engine = create_engine(DB_PATH)
    query = "SELECT * FROM search_results"
    df = pd.read_sql(query, engine)
    
    output_file = "google_search_results.csv"
    df.to_csv(output_file, index=False)
    logger.info(f"Exported {len(df)} results to {output_file}")
    return output_file

if __name__ == "__main__":
    asyncio.run(main())
    # Uncomment to export results to CSV after scraping
    # export_results_to_csv()