"""Database module for storing Bloomberg articles."""
import os
import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BloombergDB:
    """Database for storing Bloomberg articles."""
    
    def __init__(self, db_path: str = 'data/bloomberg_nuclear.db'):
        """Initialize the database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # Connect to the database
        self._connect()
        
        # Create tables if they don't exist
        self._create_tables()
    
    def _connect(self):
        """Connect to the database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {str(e)}")
            raise
    
    def _create_tables(self):
        """Create tables if they don't exist."""
        try:
            # Create articles table
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    title TEXT,
                    date TEXT,
                    publish_date TEXT,
                    text TEXT,
                    summary TEXT,
                    authors TEXT,
                    keywords TEXT,
                    top_image TEXT,
                    html_content TEXT,
                    scraped_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create metadata table for tracking scraping progress
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS scraping_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_date TEXT,
                    end_date TEXT,
                    query TEXT,
                    last_scraped_date TEXT,
                    total_articles INTEGER,
                    status TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.conn.commit()
            logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            logger.error(f"Error creating tables: {str(e)}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def insert_article(self, article: Dict) -> bool:
        """Insert an article into the database.
        
        Args:
            article: Article data dictionary
            
        Returns:
            bool: True if the article was inserted, False if it already exists
        """
        try:
            # Check if URL already exists
            self.cursor.execute("SELECT url FROM articles WHERE url = ?", (article.get('url'),))
            if self.cursor.fetchone():
                logger.debug(f"Article already exists: {article.get('url')}")
                return False
            
            # Prepare data for insertion
            authors = json.dumps(article.get('authors', [])) if isinstance(article.get('authors'), list) else article.get('authors', '[]')
            keywords = json.dumps(article.get('keywords', [])) if isinstance(article.get('keywords'), list) else article.get('keywords', '[]')
            
            # Insert article
            self.cursor.execute('''
                INSERT INTO articles (
                    url, title, date, publish_date, text, summary, 
                    authors, keywords, top_image, html_content, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article.get('url', ''),
                article.get('title', ''),
                article.get('date', ''),
                article.get('publish_date', ''),
                article.get('text', ''),
                article.get('summary', ''),
                authors,
                keywords,
                article.get('top_image', ''),
                article.get('html_content', ''),
                article.get('scraped_at', datetime.now().isoformat())
            ))
            
            self.conn.commit()
            logger.info(f"Article inserted: {article.get('title')[:50]}...")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error inserting article: {str(e)}")
            self.conn.rollback()
            return False
    
    def insert_articles(self, articles: List[Dict]) -> int:
        """Insert multiple articles into the database.
        
        Args:
            articles: List of article data dictionaries
            
        Returns:
            int: Number of articles inserted
        """
        inserted_count = 0
        for article in articles:
            if self.insert_article(article):
                inserted_count += 1
        
        logger.info(f"Inserted {inserted_count} out of {len(articles)} articles")
        return inserted_count
    
    def update_scraping_metadata(self, 
                               start_date: str, 
                               end_date: str, 
                               query: str,
                               last_scraped_date: str,
                               total_articles: int,
                               status: str) -> int:
        """Update scraping metadata.
        
        Args:
            start_date: Start date of the scraping period
            end_date: End date of the scraping period
            query: Search query
            last_scraped_date: Last date that was scraped
            total_articles: Total number of articles scraped
            status: Status of the scraping process
            
        Returns:
            int: ID of the metadata record
        """
        try:
            # Check if metadata exists for this query and date range
            self.cursor.execute(
                "SELECT id FROM scraping_metadata WHERE start_date = ? AND end_date = ? AND query = ?", 
                (start_date, end_date, query)
            )
            result = self.cursor.fetchone()
            
            if result:
                # Update existing record
                self.cursor.execute('''
                    UPDATE scraping_metadata 
                    SET last_scraped_date = ?, total_articles = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (last_scraped_date, total_articles, status, result['id']))
                metadata_id = result['id']
            else:
                # Insert new record
                self.cursor.execute('''
                    INSERT INTO scraping_metadata (
                        start_date, end_date, query, last_scraped_date, total_articles, status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (start_date, end_date, query, last_scraped_date, total_articles, status))
                metadata_id = self.cursor.lastrowid
            
            self.conn.commit()
            logger.info(f"Scraping metadata updated: {query} from {start_date} to {end_date}")
            return metadata_id
            
        except sqlite3.Error as e:
            logger.error(f"Error updating scraping metadata: {str(e)}")
            self.conn.rollback()
            return -1
    
    def get_scraping_metadata(self, start_date: str, end_date: str, query: str) -> Optional[Dict]:
        """Get scraping metadata for a specific query and date range.
        
        Args:
            start_date: Start date of the scraping period
            end_date: End date of the scraping period
            query: Search query
            
        Returns:
            Optional[Dict]: Metadata record or None if not found
        """
        try:
            self.cursor.execute(
                "SELECT * FROM scraping_metadata WHERE start_date = ? AND end_date = ? AND query = ?", 
                (start_date, end_date, query)
            )
            result = self.cursor.fetchone()
            
            if result:
                return dict(result)
            return None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting scraping metadata: {str(e)}")
            return None
    
    def get_article_count(self) -> int:
        """Get the total number of articles in the database.
        
        Returns:
            int: Number of articles
        """
        try:
            self.cursor.execute("SELECT COUNT(*) as count FROM articles")
            result = self.cursor.fetchone()
            return result['count'] if result else 0
        except sqlite3.Error as e:
            logger.error(f"Error getting article count: {str(e)}")
            return 0
    
    def get_articles_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Get articles within a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List[Dict]: List of articles
        """
        try:
            self.cursor.execute(
                "SELECT * FROM articles WHERE date BETWEEN ? AND ? ORDER BY date",
                (start_date, end_date)
            )
            return [dict(row) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting articles by date range: {str(e)}")
            return []
    
    def get_article_by_url(self, url: str) -> Optional[Dict]:
        """Get an article by URL.
        
        Args:
            url: Article URL
            
        Returns:
            Optional[Dict]: Article data or None if not found
        """
        try:
            self.cursor.execute("SELECT * FROM articles WHERE url = ?", (url,))
            result = self.cursor.fetchone()
            return dict(result) if result else None
        except sqlite3.Error as e:
            logger.error(f"Error getting article by URL: {str(e)}")
            return None
    
    def export_to_json(self, output_path: str) -> bool:
        """Export all articles to a JSON file.
        
        Args:
            output_path: Path to the output JSON file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.cursor.execute("SELECT * FROM articles")
            articles = [dict(row) for row in self.cursor.fetchall()]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(articles)} articles to {output_path}")
            return True
        except (sqlite3.Error, IOError) as e:
            logger.error(f"Error exporting to JSON: {str(e)}")
            return False 