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
    created_at = Column(DateTime)
    
def init_db(database_name='IAEA'):
    """Initialize the database connection."""
    # Create database directory if it doesn't exist
    os.makedirs('data/db', exist_ok=True)
    
    # Create SQLite database
    engine = create_engine(f'sqlite:///data/db/{database_name}.db')
    
    # Create tables
    Base.metadata.create_all(engine)
    
    # Create session factory
    Session = sessionmaker(bind=engine)
    return Session()
