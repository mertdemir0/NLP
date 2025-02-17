"""
HTML document parser for nuclear energy content analysis.
"""

from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import requests
import logging
from pathlib import Path
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

class HTMLParser:
    """Parser for extracting content from HTML documents."""

    def __init__(self):
        """Initialize the HTML parser."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.date_patterns = [
            r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b'
        ]

    def parse_url(self, url: str) -> Dict[str, str]:
        """
        Parse content from a URL.

        Args:
            url: URL to parse

        Returns:
            Dictionary containing extracted content and metadata
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract content
            content = self._extract_main_content(soup)
            metadata = self._extract_metadata(soup, url)
            
            return {
                'text': content,
                'metadata': metadata,
                'success': True,
                'error': None,
                'url': url
            }
            
        except Exception as e:
            logger.error(f"Error parsing URL {url}: {str(e)}")
            return {
                'text': "",
                'metadata': {},
                'success': False,
                'error': str(e),
                'url': url
            }

    def parse_html_file(self, file_path: str) -> Dict[str, str]:
        """
        Parse content from a local HTML file.

        Args:
            file_path: Path to HTML file

        Returns:
            Dictionary containing extracted content and metadata
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'lxml')
            
            content = self._extract_main_content(soup)
            metadata = self._extract_metadata(soup, file_path)
            
            return {
                'text': content,
                'metadata': metadata,
                'success': True,
                'error': None,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {str(e)}")
            return {
                'text': "",
                'metadata': {},
                'success': False,
                'error': str(e),
                'file_path': file_path
            }

    def parse_multiple_files(self, directory: str, recursive: bool = True) -> List[Dict[str, str]]:
        """
        Parse multiple HTML files from a directory.

        Args:
            directory: Directory containing HTML files
            recursive: Whether to search subdirectories

        Returns:
            List of dictionaries containing extracted content
        """
        results = []
        path = Path(directory)
        
        # Get all HTML files
        pattern = '**/*.html' if recursive else '*.html'
        for html_file in path.glob(pattern):
            logger.info(f"Processing {html_file}")
            result = self.parse_html_file(str(html_file))
            results.append(result)
            
        return results

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from HTML document."""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        
        # Try to find main content area
        main_content = None
        
        # Check common content containers
        content_selectors = [
            'article',
            'main',
            '[role="main"]',
            '.main-content',
            '#main-content',
            '.post-content',
            '.article-content'
        ]
        
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        # If no main content found, use body
        if not main_content:
            main_content = soup.body
        
        if main_content:
            # Get text and clean it
            text = main_content.get_text(separator=' ', strip=True)
            # Remove extra whitespace
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        
        return ""

    def _extract_metadata(self, soup: BeautifulSoup, source: str) -> Dict[str, str]:
        """Extract metadata from HTML document."""
        metadata = {}
        
        # Extract title
        metadata['title'] = self._get_title(soup)
        
        # Extract date
        metadata['date'] = self._get_date(soup)
        
        # Extract author
        metadata['author'] = self._get_author(soup)
        
        # Extract description
        metadata['description'] = self._get_description(soup)
        
        # Add source information
        metadata['source'] = source
        
        return metadata

    def _get_title(self, soup: BeautifulSoup) -> str:
        """Extract title from HTML document."""
        # Try meta title first
        meta_title = soup.find('meta', property='og:title') or soup.find('meta', property='twitter:title')
        if meta_title:
            return meta_title.get('content', '')
        
        # Try HTML title
        title_tag = soup.title
        if title_tag:
            return title_tag.string.strip()
        
        # Try h1
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text(strip=True)
        
        return ""

    def _get_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date from HTML document."""
        # Try meta date
        for meta in soup.find_all('meta'):
            if meta.get('property') in ['article:published_time', 'og:published_time']:
                return meta.get('content', '')
        
        # Try common date elements
        date_elements = soup.find_all(['time', 'span', 'div'], class_=re.compile(r'date|time|publish'))
        
        for element in date_elements:
            # Check datetime attribute
            date_str = element.get('datetime', '') or element.get('content', '')
            if date_str:
                return self._parse_date(date_str)
            
            # Check text content
            text = element.get_text(strip=True)
            for pattern in self.date_patterns:
                match = re.search(pattern, text)
                if match:
                    return self._parse_date(match.group(0))
        
        return ""

    def _get_author(self, soup: BeautifulSoup) -> str:
        """Extract author from HTML document."""
        # Try meta author
        meta_author = soup.find('meta', property='author') or soup.find('meta', name='author')
        if meta_author:
            return meta_author.get('content', '')
        
        # Try common author elements
        author_elements = soup.find_all(['a', 'span', 'div'], class_=re.compile(r'author|byline'))
        
        for element in author_elements:
            author = element.get_text(strip=True)
            if author and len(author) < 100:  # Avoid getting large text blocks
                return author
        
        return ""

    def _get_description(self, soup: BeautifulSoup) -> str:
        """Extract description from HTML document."""
        # Try meta description
        meta_desc = (
            soup.find('meta', property='og:description') or
            soup.find('meta', property='twitter:description') or
            soup.find('meta', name='description')
        )
        
        if meta_desc:
            return meta_desc.get('content', '')
        
        return ""

    def _parse_date(self, date_str: str) -> str:
        """Parse and standardize date string."""
        date_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return ""