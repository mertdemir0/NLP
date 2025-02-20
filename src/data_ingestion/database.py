"""Database module for storing scraped articles."""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()

class RawArticle(Base):
    """Raw article table for storing unprocessed articles."""
    __tablename__ = 'raw'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    content = Column(Text)
    url = Column(String(500), unique=True)
    date = Column(String(100))  # Keep as string initially since date formats might vary
    topics = Column(JSON)  # Store topics as JSON array
    source = Column(String(50))
    type = Column(String(50))  # Store article type (News Story, Press Release, etc.)
    created_at = Column(DateTime)

class BloombergArticle(Base):
    """Model for Bloomberg articles from Google search."""
    __tablename__ = 'bloomberg_articles'
    
    id = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(Text)
    url = Column(String, unique=True)
    summary = Column(Text)
    date = Column(String)
    created_at = Column(DateTime)

def init_db(database_name='IAEA'):
    """Initialize the database connection."""
    # Get the project root directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    
    # Create database directory if it doesn't exist
    db_dir = os.path.join(project_root, 'data', 'db')
    os.makedirs(db_dir, exist_ok=True)
    
    # Create SQLite database with absolute path
    db_path = os.path.join(db_dir, f'{database_name}.db')
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Create tables
    Base.metadata.create_all(engine)
    
    # Create session factory
    Session = sessionmaker(bind=engine)
    return Session()
