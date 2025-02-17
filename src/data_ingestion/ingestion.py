"""
Main data ingestion module for nuclear energy content analysis.
"""

from typing import Dict, List, Optional, Union
import logging
from pathlib import Path
import json
from datetime import datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from .pdf_parser import PDFParser
from .html_parser import HTMLParser

logger = logging.getLogger(__name__)

class DataIngestion:
    """Main class for handling data ingestion from various sources."""

    def __init__(self, config: Dict = None):
        """
        Initialize the data ingestion module.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.pdf_parser = PDFParser()
        self.html_parser = HTMLParser()
        self.supported_formats = {
            '.pdf': self.pdf_parser.parse_pdf,
            '.html': self.html_parser.parse_html_file,
            '.htm': self.html_parser.parse_html_file
        }

    def ingest_file(self, file_path: str) -> Dict[str, str]:
        """
        Ingest a single file.

        Args:
            file_path: Path to the file to ingest

        Returns:
            Dictionary containing extracted content and metadata
        """
        path = Path(file_path)
        
        if path.suffix.lower() not in self.supported_formats:
            return {
                'text': "",
                'metadata': {},
                'success': False,
                'error': f"Unsupported file format: {path.suffix}",
                'file_path': file_path
            }
        
        parser = self.supported_formats[path.suffix.lower()]
        return parser(file_path)

    def ingest_directory(self, 
                        directory: str,
                        recursive: bool = True,
                        max_workers: int = 4) -> List[Dict[str, str]]:
        """
        Ingest all supported files from a directory.

        Args:
            directory: Directory to process
            recursive: Whether to search subdirectories
            max_workers: Maximum number of concurrent workers

        Returns:
            List of dictionaries containing extracted content
        """
        path = Path(directory)
        results = []
        
        # Get all supported files
        files = []
        pattern = '**/*' if recursive else '*'
        for file_path in path.glob(pattern):
            if file_path.suffix.lower() in self.supported_formats:
                files.append(str(file_path))
        
        # Process files concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(self.ingest_file, file): file
                for file in files
            }
            
            for future in as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {file}: {str(e)}")
                    results.append({
                        'text': "",
                        'metadata': {},
                        'success': False,
                        'error': str(e),
                        'file_path': file
                    })
        
        return results

    def ingest_urls(self, urls: List[str], max_workers: int = 4) -> List[Dict[str, str]]:
        """
        Ingest content from multiple URLs.

        Args:
            urls: List of URLs to process
            max_workers: Maximum number of concurrent workers

        Returns:
            List of dictionaries containing extracted content
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(self.html_parser.parse_url, url): url
                for url in urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing {url}: {str(e)}")
                    results.append({
                        'text': "",
                        'metadata': {},
                        'success': False,
                        'error': str(e),
                        'url': url
                    })
        
        return results

    def save_results(self, results: List[Dict[str, str]], output_dir: str) -> None:
        """
        Save ingestion results to files.

        Args:
            results: List of ingestion results
            output_dir: Directory to save results
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save individual results
        for i, result in enumerate(results):
            if result['success']:
                # Generate filename from metadata or use index
                filename = self._generate_filename(result, i)
                
                # Save as JSON
                with open(output_path / f"{filename}.json", 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Save summary
        summary = self._generate_summary(results)
        with open(output_path / "ingestion_summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # Save as CSV for easy viewing
        df = pd.DataFrame([
            {
                'source': result.get('url', result.get('file_path', '')),
                'success': result['success'],
                'error': result.get('error', ''),
                'title': result.get('metadata', {}).get('title', ''),
                'date': result.get('metadata', {}).get('date', ''),
                'author': result.get('metadata', {}).get('author', '')
            }
            for result in results
        ])
        df.to_csv(output_path / "ingestion_results.csv", index=False)

    def _generate_filename(self, result: Dict[str, str], index: int) -> str:
        """Generate a filename for saving results."""
        # Try to use title from metadata
        title = result.get('metadata', {}).get('title', '')
        if title:
            # Clean title for use as filename
            title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
            title = title.strip().replace(' ', '_')[:100]  # Limit length
            return title
        
        # Use source information if available
        if 'url' in result:
            return f"url_{index}"
        elif 'file_path' in result:
            return f"file_{index}"
        
        return f"document_{index}"

    def _generate_summary(self, results: List[Dict[str, str]]) -> Dict:
        """Generate summary of ingestion results."""
        total = len(results)
        successful = sum(1 for r in results if r['success'])
        failed = total - successful
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_documents': total,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total if total > 0 else 0,
            'errors': [
                {
                    'source': r.get('url', r.get('file_path', '')),
                    'error': r['error']
                }
                for r in results if not r['success']
            ]
        }