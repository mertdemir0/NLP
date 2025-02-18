"""Simple test script for the news scraper."""
import sqlite3
from pathlib import Path

def create_db():
    """Create the SQLite database and tables."""
    db_path = "data/articles.db"
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
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
        
        # Create sentiment table
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
    
    print("Database created successfully!")

def test_db():
    """Test database operations."""
    db_path = "data/articles.db"
    
    # Insert test article
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        test_article = {
            'title': 'Test Article',
            'url': 'https://example.com/test',
            'content': 'This is a test article content.',
            'summary': 'Test summary',
            'published_date': '2025-02-18',
            'source': 'Test Source',
            'author': 'Test Author',
            'keywords': 'test,article'
        }
        
        cursor.execute('''
            INSERT OR IGNORE INTO articles 
            (title, url, content, summary, published_date, source, author, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            test_article['title'],
            test_article['url'],
            test_article['content'],
            test_article['summary'],
            test_article['published_date'],
            test_article['source'],
            test_article['author'],
            test_article['keywords']
        ))
        
        conn.commit()
    
    # Read test article
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM articles')
        articles = [dict(row) for row in cursor.fetchall()]
        
        print("\nArticles in database:")
        for article in articles:
            print(f"\nTitle: {article['title']}")
            print(f"Source: {article['source']}")
            print(f"Date: {article['published_date']}")
            print(f"URL: {article['url']}")
            print("-" * 80)

if __name__ == "__main__":
    create_db()
    test_db()
