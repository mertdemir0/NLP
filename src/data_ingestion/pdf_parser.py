"""
PDF document parser for nuclear energy content analysis.
"""

from typing import Dict, List, Optional
import PyPDF2
import logging
from pathlib import Path
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class PDFParser:
    """Parser for extracting content from PDF documents."""

    def __init__(self):
        """Initialize the PDF parser."""
        self.metadata_patterns = {
            'date': r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',
            'author': r'Author[s]?:?\s*([\w\s,\.]+)',
            'title': r'Title:?\s*([\w\s,\.-]+)',
        }

    def parse_pdf(self, file_path: str) -> Dict[str, str]:
        """
        Parse a PDF file and extract its content and metadata.

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            with open(file_path, 'rb') as file:
                # Create PDF reader object
                reader = PyPDF2.PdfReader(file)
                
                # Extract text from all pages
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                
                # Extract metadata
                metadata = self._extract_metadata(reader, text)
                
                return {
                    'text': text,
                    'metadata': metadata,
                    'success': True,
                    'error': None
                }
                
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {str(e)}")
            return {
                'text': "",
                'metadata': {},
                'success': False,
                'error': str(e)
            }

    def parse_multiple_pdfs(self, directory: str, recursive: bool = True) -> List[Dict[str, str]]:
        """
        Parse multiple PDF files from a directory.

        Args:
            directory: Directory containing PDF files
            recursive: Whether to search subdirectories

        Returns:
            List of dictionaries containing extracted content
        """
        results = []
        path = Path(directory)
        
        # Get all PDF files
        pattern = '**/*.pdf' if recursive else '*.pdf'
        for pdf_file in path.glob(pattern):
            logger.info(f"Processing {pdf_file}")
            result = self.parse_pdf(str(pdf_file))
            result['file_path'] = str(pdf_file)
            results.append(result)
            
        return results

    def _extract_metadata(self, reader: PyPDF2.PdfReader, text: str) -> Dict[str, str]:
        """Extract metadata from PDF document."""
        metadata = {}
        
        # Try to get metadata from PDF info
        if reader.metadata:
            metadata.update({
                'title': reader.metadata.get('/Title', ''),
                'author': reader.metadata.get('/Author', ''),
                'creation_date': reader.metadata.get('/CreationDate', ''),
                'modification_date': reader.metadata.get('/ModDate', ''),
                'producer': reader.metadata.get('/Producer', '')
            })
        
        # Extract information from text using patterns
        for key, pattern in self.metadata_patterns.items():
            if key not in metadata or not metadata[key]:
                match = re.search(pattern, text)
                if match:
                    metadata[key] = match.group(1).strip()
        
        # Clean up dates
        metadata['date'] = self._parse_date(metadata.get('creation_date', ''))
        
        return metadata

    def _parse_date(self, date_str: str) -> str:
        """Parse and standardize date string."""
        date_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%B %d, %Y',
            '%b %d, %Y',
            "D:%Y%m%d%H%M%S",  # PDF date format
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return ''

    def extract_tables(self, file_path: str) -> List[List[str]]:
        """
        Extract tables from PDF document.

        Args:
            file_path: Path to the PDF file

        Returns:
            List of tables, where each table is a list of rows
        """
        # Note: This is a placeholder. For proper table extraction,
        # consider using specialized libraries like tabula-py or camelot-py
        return []

    def get_document_structure(self, file_path: str) -> Dict[str, List[str]]:
        """
        Extract document structure (sections, subsections).

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary containing document structure
        """
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Extract outlines if available
                structure = {'sections': [], 'subsections': []}
                
                # Note: This is a basic implementation
                # For better results, consider using regex patterns to identify
                # section headers based on formatting or numbering
                
                return structure
                
        except Exception as e:
            logger.error(f"Error extracting structure from {file_path}: {str(e)}")
            return {'sections': [], 'subsections': []}