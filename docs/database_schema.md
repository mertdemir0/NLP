# Database Schema Documentation

## Overview
The database is designed to store and manage nuclear energy news articles from two main sources: Bloomberg and IAEA.

## Tables

### Bloomberg Articles (`bloomberg_articles`)

| Column         | Type      | Description                               | Constraints           |
|---------------|-----------|-------------------------------------------|--------------------|
| id            | INTEGER   | Unique identifier                         | PRIMARY KEY, AUTOINCREMENT |
| title         | TEXT      | Article title                             | NOT NULL          |
| content       | TEXT      | Full article content                      | NOT NULL          |
| published_date| TEXT      | Publication date                          |                   |
| url           | TEXT      | Article URL                               | UNIQUE, NOT NULL  |
| source        | TEXT      | Source identifier                         | NOT NULL          |
| created_at    | TIMESTAMP | Record creation timestamp                 | DEFAULT CURRENT_TIMESTAMP |

#### Indexes
- `idx_bloomberg_url`: Index on URL for fast lookups
- `idx_bloomberg_source`: Index on source for filtering
- `idx_bloomberg_date`: Index on published_date for temporal queries

### IAEA Articles (`iaea_articles`)

| Column         | Type      | Description                               | Constraints           |
|---------------|-----------|-------------------------------------------|--------------------|
| id            | INTEGER   | Unique identifier                         | PRIMARY KEY, AUTOINCREMENT |
| title         | TEXT      | Article title                             | NOT NULL          |
| content       | TEXT      | Full article content                      | NOT NULL          |
| published_date| TEXT      | Publication date                          |                   |
| url           | TEXT      | Article URL                               | UNIQUE, NOT NULL  |
| source        | TEXT      | Source identifier                         | NOT NULL          |
| created_at    | TIMESTAMP | Record creation timestamp                 | DEFAULT CURRENT_TIMESTAMP |

#### Indexes
- `idx_iaea_url`: Index on URL for fast lookups
- `idx_iaea_source`: Index on source for filtering
- `idx_iaea_date`: Index on published_date for temporal queries

## Key Features

1. **Separate Tables**
   - Independent tables for each source
   - Same schema for consistency
   - Allows source-specific queries and analysis

2. **Indexing Strategy**
   - URL indexing for duplicate prevention
   - Date indexing for temporal analysis
   - Source indexing for filtering

3. **Data Integrity**
   - Primary key constraints
   - Unique URL constraints
   - NOT NULL constraints on essential fields

4. **Temporal Tracking**
   - Published date for article timing
   - Creation timestamp for database operations

## Common Queries

### Article Retrieval
```sql
-- Get recent Bloomberg articles
SELECT * FROM bloomberg_articles 
ORDER BY published_date DESC 
LIMIT 10;

-- Get IAEA articles by month
SELECT strftime('%Y-%m', published_date) as month,
       COUNT(*) as count
FROM iaea_articles
GROUP BY month
ORDER BY month DESC;
```

### Statistics
```sql
-- Get total article counts
SELECT 
    (SELECT COUNT(*) FROM bloomberg_articles) as bloomberg_count,
    (SELECT COUNT(*) FROM iaea_articles) as iaea_count;

-- Get monthly distribution
SELECT 
    strftime('%Y-%m', published_date) as month,
    COUNT(*) as article_count
FROM bloomberg_articles
GROUP BY month
ORDER BY month DESC;
```

## Best Practices

1. **Data Insertion**
   - Use `INSERT OR IGNORE` to handle duplicates
   - Always provide URL for uniqueness check
   - Use parameterized queries to prevent SQL injection

2. **Querying**
   - Use indexes for better performance
   - Filter by date ranges when possible
   - Use appropriate table for source-specific queries

3. **Maintenance**
   - Regular backup of database file
   - Index optimization if needed
   - Monitor database size and growth

## Tools and Access

- Database File: `data/articles.db`
- Access via SQLite3 or Python's sqlite3 module
- Managed through `ArticleDB` class in `src/database/models.py`
