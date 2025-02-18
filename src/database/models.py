"""SQLite database models for storing articles."""
from datetime import datetime
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional

class ArticleDB:
    def __init__(self, db_path: str = "data/articles.db"):
        """Initialize the article database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._create_tables()
    
    def _create_tables(self):
        """Create the necessary database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create articles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL,
                    summary TEXT,
                    published_date TEXT,
                    source TEXT,
                    author TEXT,
                    keywords TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create sentiment table for future analysis
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sentiment_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER,
                    sentiment_score REAL,
                    sentiment_label TEXT,
                    analyzed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles (id)
                )
            ''')
            
            conn.commit()
    
    def insert_article(self, article: Dict) -> int:
        """Insert a new article into the database.
        
        Args:
            article: Dictionary containing article data
                Required keys: title, url, content
                Optional keys: summary, published_date, source, author, keywords
        
        Returns:
            int: ID of the inserted article
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Convert keywords list to comma-separated string if present
            if 'keywords' in article and isinstance(article['keywords'], list):
                article['keywords'] = ','.join(article['keywords'])
            
            # Prepare query
            query = '''
                INSERT OR IGNORE INTO articles 
                (title, url, content, summary, published_date, source, author, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            # Execute query with values
            cursor.execute(query, (
                article['title'],
                article['url'],
                article['content'],
                article.get('summary'),
                article.get('published_date'),
                article.get('source'),
                article.get('author'),
                article.get('keywords')
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_article_by_url(self, url: str) -> Optional[Dict]:
        """Retrieve an article by its URL.
        
        Args:
            url: The URL of the article to retrieve
            
        Returns:
            Dict or None: Article data if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM articles WHERE url = ?', (url,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def get_articles_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """Retrieve articles within a date range.
        
        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            
        Returns:
            List[Dict]: List of articles within the date range
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM articles 
                WHERE published_date BETWEEN ? AND ?
                ORDER BY published_date DESC
            ''', (start_date, end_date))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_all_articles(self) -> List[Dict]:
        """Retrieve all articles from the database.
        
        Returns:
            List[Dict]: List of all articles
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM articles ORDER BY published_date DESC')
            return [dict(row) for row in cursor.fetchall()]
    
    def update_sentiment(self, article_id: int, sentiment_score: float, sentiment_label: str):
        """Update or insert sentiment analysis for an article.
        
        Args:
            article_id: ID of the article
            sentiment_score: Numerical sentiment score
            sentiment_label: Sentiment label (e.g., 'positive', 'negative', 'neutral')
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO sentiment_analysis 
                (article_id, sentiment_score, sentiment_label)
                VALUES (?, ?, ?)
            ''', (article_id, sentiment_score, sentiment_label))
            
            conn.commit()
