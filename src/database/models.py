"""Database models for storing articles."""
import sqlite3
from typing import Dict, Optional, List
import json
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class ArticleDB:
    """SQLite database for storing articles."""
    
    def __init__(self, db_path: str = 'data/articles.db'):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # If database exists, rename it as backup before creating new schema
        if os.path.exists(db_path):
            backup_path = f"{db_path}.backup"
            try:
                os.rename(db_path, backup_path)
                logger.info(f"Created database backup: {backup_path}")
            except Exception as e:
                logger.error(f"Failed to create database backup: {str(e)}")
        
        self.db_path = db_path
        self._create_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            published_date TEXT,
            url TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
        CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
        CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(published_date);
        """
        
        try:
            with self._get_connection() as conn:
                conn.executescript(create_table_sql)
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise
    
    def insert_article(self, article: Dict) -> bool:
        """Insert a new article into the database.
        
        Args:
            article: Article data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        insert_sql = """
        INSERT OR IGNORE INTO articles (title, content, published_date, url, source)
        VALUES (?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(insert_sql, (
                    article['title'],
                    article['content'],
                    article['date'],  # Map 'date' to 'published_date'
                    article['url'],
                    article['source']
                ))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error inserting article: {str(e)}")
            return False
    
    def get_article_by_url(self, url: str) -> Optional[Dict]:
        """Get article by URL.
        
        Args:
            url: Article URL
            
        Returns:
            Dict or None: Article data if found
        """
        select_sql = "SELECT * FROM articles WHERE url = ?"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, (url,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'title': row[1],
                        'content': row[2],
                        'date': row[3],  # Map 'published_date' to 'date'
                        'url': row[4],
                        'source': row[5],
                        'created_at': row[6]
                    }
                return None
        except sqlite3.Error as e:
            logger.error(f"Error getting article: {str(e)}")
            return None
    
    def get_all_articles(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all articles from the database.
        
        Args:
            limit: Optional limit on number of articles to return
            
        Returns:
            List[Dict]: List of article dictionaries
        """
        select_sql = "SELECT * FROM articles ORDER BY published_date DESC"
        if limit:
            select_sql += f" LIMIT {limit}"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql)
                rows = cursor.fetchall()
                
                return [{
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'date': row[3],  # Map 'published_date' to 'date'
                    'url': row[4],
                    'source': row[5],
                    'created_at': row[6]
                } for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error getting articles: {str(e)}")
            return []
    
    def get_articles_by_source(self, source: str) -> List[Dict]:
        """Get articles from a specific source.
        
        Args:
            source: Source name (e.g., 'IAEA', 'Bloomberg')
            
        Returns:
            List[Dict]: List of article dictionaries
        """
        select_sql = "SELECT * FROM articles WHERE source = ? ORDER BY published_date DESC"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, (source,))
                rows = cursor.fetchall()
                
                return [{
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'date': row[3],  # Map 'published_date' to 'date'
                    'url': row[4],
                    'source': row[5],
                    'created_at': row[6]
                } for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error getting articles by source: {str(e)}")
            return []
    
    def get_article_count(self) -> int:
        """Get total number of articles in database.
        
        Returns:
            int: Number of articles
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM articles")
                return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Error getting article count: {str(e)}")
            return 0
    
    def get_source_statistics(self) -> Dict[str, int]:
        """Get article count by source.
        
        Returns:
            Dict[str, int]: Dictionary mapping source names to article counts
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT source, COUNT(*) FROM articles GROUP BY source")
                return dict(cursor.fetchall())
        except sqlite3.Error as e:
            logger.error(f"Error getting source statistics: {str(e)}")
            return {}
