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
        self.db_path = db_path
        self._create_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def _create_tables(self):
        """Create necessary database tables if they don't exist."""
        create_tables_sql = """
        -- Bloomberg articles table
        CREATE TABLE IF NOT EXISTS bloomberg_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            published_date TEXT,
            url TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_bloomberg_url ON bloomberg_articles(url);
        CREATE INDEX IF NOT EXISTS idx_bloomberg_source ON bloomberg_articles(source);
        CREATE INDEX IF NOT EXISTS idx_bloomberg_date ON bloomberg_articles(published_date);
        
        -- IAEA articles table
        CREATE TABLE IF NOT EXISTS iaea_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            published_date TEXT,
            url TEXT UNIQUE NOT NULL,
            source TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_iaea_url ON iaea_articles(url);
        CREATE INDEX IF NOT EXISTS idx_iaea_source ON iaea_articles(source);
        CREATE INDEX IF NOT EXISTS idx_iaea_date ON iaea_articles(published_date);
        """
        
        try:
            with self._get_connection() as conn:
                conn.executescript(create_tables_sql)
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise
    
    def _row_to_dict(self, row: tuple) -> Dict:
        """Convert database row to dictionary."""
        return {
            'id': row[0],
            'title': row[1],
            'content': row[2],
            'date': row[3],  # Map 'published_date' to 'date'
            'url': row[4],
            'source': row[5],
            'created_at': row[6]
        }
    
    def insert_bloomberg_article(self, article: Dict) -> bool:
        """Insert a new Bloomberg article."""
        return self._insert_article(article, 'bloomberg_articles')
    
    def insert_iaea_article(self, article: Dict) -> bool:
        """Insert a new IAEA article."""
        return self._insert_article(article, 'iaea_articles')
    
    def _insert_article(self, article: Dict, table: str) -> bool:
        """Insert an article into specified table."""
        insert_sql = f"""
        INSERT OR IGNORE INTO {table} (title, content, published_date, url, source)
        VALUES (?, ?, ?, ?, ?)
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(insert_sql, (
                    article['title'],
                    article['content'],
                    article['date'],
                    article['url'],
                    article['source']
                ))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error inserting article into {table}: {str(e)}")
            return False
    
    def get_bloomberg_articles(self, limit: Optional[int] = None) -> List[Dict]:
        """Get Bloomberg articles."""
        return self._get_articles('bloomberg_articles', limit)
    
    def get_iaea_articles(self, limit: Optional[int] = None) -> List[Dict]:
        """Get IAEA articles."""
        return self._get_articles('iaea_articles', limit)
    
    def _get_articles(self, table: str, limit: Optional[int] = None) -> List[Dict]:
        """Get articles from specified table."""
        select_sql = f"SELECT * FROM {table} ORDER BY published_date DESC"
        if limit:
            select_sql += f" LIMIT {limit}"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql)
                rows = cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error getting articles from {table}: {str(e)}")
            return []
    
    def get_article_by_url(self, url: str) -> Optional[Dict]:
        """Get article by URL from either table."""
        # Try Bloomberg first
        article = self._get_article_by_url(url, 'bloomberg_articles')
        if article:
            return article
        
        # Try IAEA if not found in Bloomberg
        return self._get_article_by_url(url, 'iaea_articles')
    
    def _get_article_by_url(self, url: str, table: str) -> Optional[Dict]:
        """Get article by URL from specified table."""
        select_sql = f"SELECT * FROM {table} WHERE url = ?"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(select_sql, (url,))
                row = cursor.fetchone()
                return self._row_to_dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting article from {table}: {str(e)}")
            return None
    
    def get_article_count(self) -> Dict[str, int]:
        """Get article count for each source."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                counts = {}
                
                # Get Bloomberg count
                cursor.execute("SELECT COUNT(*) FROM bloomberg_articles")
                counts['Bloomberg'] = cursor.fetchone()[0]
                
                # Get IAEA count
                cursor.execute("SELECT COUNT(*) FROM iaea_articles")
                counts['IAEA'] = cursor.fetchone()[0]
                
                # Add total
                counts['Total'] = counts['Bloomberg'] + counts['IAEA']
                
                return counts
        except sqlite3.Error as e:
            logger.error(f"Error getting article counts: {str(e)}")
            return {'Bloomberg': 0, 'IAEA': 0, 'Total': 0}
    
    def get_source_statistics(self) -> Dict[str, Dict[str, int]]:
        """Get detailed statistics for each source."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                stats = {}
                
                for table in ['bloomberg_articles', 'iaea_articles']:
                    source = 'Bloomberg' if table == 'bloomberg_articles' else 'IAEA'
                    
                    # Get total articles
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    total = cursor.fetchone()[0]
                    
                    # Get articles per month
                    cursor.execute(f"""
                        SELECT strftime('%Y-%m', published_date) as month,
                               COUNT(*) as count
                        FROM {table}
                        GROUP BY month
                        ORDER BY month DESC
                        LIMIT 12
                    """)
                    monthly = dict(cursor.fetchall())
                    
                    stats[source] = {
                        'total': total,
                        'monthly': monthly
                    }
                
                return stats
        except sqlite3.Error as e:
            logger.error(f"Error getting source statistics: {str(e)}")
            return {}
