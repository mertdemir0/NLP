"""Module for analyzing nuclear energy news articles."""
import os
import pandas as pd
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from collections import Counter
from typing import Dict, List
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from datetime import datetime

class ArticleAnalyzer:
    """Analyzer for nuclear energy news articles."""
    
    def __init__(self):
        """Initialize the analyzer."""
        self.sia = SentimentIntensityAnalyzer()
        self.stop_words = set(stopwords.words('english'))
        
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text."""
        return self.sia.polarity_scores(text)
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """Extract keywords from text."""
        tokens = word_tokenize(text.lower())
        tokens = [t for t in tokens if t.isalnum() and t not in self.stop_words]
        word_freq = Counter(tokens)
        return [word for word, _ in word_freq.most_common(top_n)]
    
    def analyze_articles(self, articles: List[Dict]) -> Dict:
        """Analyze articles.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Dict: Analysis results
        """
        if not articles:
            return {"error": "No articles provided"}
        
        # Convert to DataFrame
        df = pd.DataFrame(articles)
        
        # Initialize results
        results = {
            "total_articles": len(df),
            "sources": df['source'].value_counts().to_dict(),
            "sentiment": {"positive": 0, "neutral": 0, "negative": 0},
            "top_keywords": Counter(),
            "articles": []
        }
        
        # Analyze each article
        for _, article in df.iterrows():
            # Combine title and content for analysis
            text = f"{article['title']} {article.get('content', '')}"
            
            # Sentiment analysis
            sentiment = self.analyze_sentiment(text)
            if sentiment['compound'] > 0.05:
                results['sentiment']['positive'] += 1
            elif sentiment['compound'] < -0.05:
                results['sentiment']['negative'] += 1
            else:
                results['sentiment']['neutral'] += 1
            
            # Keyword extraction
            keywords = self.extract_keywords(text)
            results['top_keywords'].update(keywords)
            
            # Store article analysis
            results['articles'].append({
                'title': article['title'],
                'source': article['source'],
                'date': article.get('date', ''),
                'url': article['url'],
                'sentiment': sentiment,
                'keywords': keywords
            })
        
        # Get overall top keywords
        results['top_keywords'] = dict(results['top_keywords'].most_common(20))
        
        return results
    
    def generate_visualizations(self, results: Dict):
        """Generate visualizations from analysis results."""
        # Create output directory
        plt.style.use('seaborn')
        output_dir = 'data/analysis'
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. Source distribution pie chart
        plt.figure(figsize=(10, 6))
        plt.pie(results['sources'].values(), labels=results['sources'].keys(), autopct='%1.1f%%')
        plt.title('Article Distribution by Source')
        plt.savefig(f'{output_dir}/source_distribution.png')
        plt.close()
        
        # 2. Sentiment distribution bar chart
        plt.figure(figsize=(10, 6))
        sentiments = results['sentiment']
        plt.bar(sentiments.keys(), sentiments.values())
        plt.title('Article Sentiment Distribution')
        plt.ylabel('Number of Articles')
        plt.savefig(f'{output_dir}/sentiment_distribution.png')
        plt.close()
        
        # 3. Word cloud of top keywords
        wordcloud = WordCloud(width=800, height=400, background_color='white')
        wordcloud.generate_from_frequencies(results['top_keywords'])
        plt.figure(figsize=(15, 8))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('Top Keywords Word Cloud')
        plt.savefig(f'{output_dir}/keyword_wordcloud.png')
        plt.close()
        
    def generate_report(self, articles: List[Dict]) -> str:
        """Generate analysis report."""
        results = self.analyze_articles(articles)
        
        if "error" in results:
            return f"Error: {results['error']}"
        
        # Generate visualizations
        self.generate_visualizations(results)
        
        # Create markdown report
        report = f"""# Nuclear Energy News Analysis Report

## Overview
- Total Articles: {results['total_articles']}
- Time Period: Last 30 days
- Sources: {len(results['sources'])} different sources

## Source Distribution
{pd.Series(results['sources']).to_markdown()}

## Sentiment Analysis
- Positive Articles: {results['sentiment']['positive']} ({results['sentiment']['positive']/results['total_articles']*100:.1f}%)
- Neutral Articles: {results['sentiment']['neutral']} ({results['sentiment']['neutral']/results['total_articles']*100:.1f}%)
- Negative Articles: {results['sentiment']['negative']} ({results['sentiment']['negative']/results['total_articles']*100:.1f}%)

## Top Keywords
{pd.Series(results['top_keywords']).head(10).to_markdown()}

## Recent Articles by Sentiment

### Most Positive Articles
{pd.DataFrame([a for a in results['articles'] if a['sentiment']['compound'] > 0.2]).sort_values('sentiment.compound', ascending=False).head(3)[['title', 'source', 'date']].to_markdown()}

### Most Negative Articles
{pd.DataFrame([a for a in results['articles'] if a['sentiment']['compound'] < -0.2]).sort_values('sentiment.compound')[['title', 'source', 'date']].to_markdown()}

## Visualizations
The following visualizations have been generated in the 'data/analysis' directory:
1. source_distribution.png - Distribution of articles by source
2. sentiment_distribution.png - Distribution of article sentiments
3. keyword_wordcloud.png - Word cloud of most frequent keywords

## Conclusions
1. Most articles come from {max(results['sources'].items(), key=lambda x: x[1])[0]}
2. The overall sentiment is {max(results['sentiment'].items(), key=lambda x: x[1])[0]}
3. Key topics include: {', '.join(list(results['top_keywords'].keys())[:5])}
"""
        
        # Save report
        os.makedirs('data/analysis', exist_ok=True)
        with open('data/analysis/report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        return report
