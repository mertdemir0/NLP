# Visualization Guide

## Overview
This guide describes the visualizations generated during the analysis of nuclear energy news articles.

## Types of Visualizations

### 1. Source Distribution (`source_distribution.png`)
- **Type**: Pie Chart
- **Purpose**: Shows the distribution of articles across different sources
- **Features**:
  - Percentage labels
  - Source labels
  - Clear color differentiation
  - Title: "Article Distribution by Source"

### 2. Sentiment Distribution (`sentiment_distribution.png`)
- **Type**: Bar Chart
- **Purpose**: Displays sentiment analysis results
- **Features**:
  - Three categories: Positive, Neutral, Negative
  - Y-axis: Number of Articles
  - Title: "Article Sentiment Distribution"
  - Clear labeling of values

### 3. Keyword Word Cloud (`keyword_wordcloud.png`)
- **Type**: Word Cloud
- **Purpose**: Visual representation of most frequent keywords
- **Features**:
  - Size indicates frequency
  - Custom dimensions (800x400)
  - White background for clarity
  - Title: "Top Keywords Word Cloud"

## Source-Specific Visualizations

### Bloomberg Analysis
- Source distribution within Bloomberg articles
- Temporal trends of Bloomberg coverage
- Sentiment analysis specific to Bloomberg articles

### IAEA Analysis
- Topic distribution in IAEA articles
- Geographic focus of IAEA reports
- Technical term frequency analysis

## Time-Based Visualizations

### Monthly Trends
- Article count per month
- Sentiment changes over time
- Topic evolution

### Comparative Analysis
- Bloomberg vs IAEA coverage over time
- Sentiment differences between sources
- Topic focus comparison

## Technical Details

### Configuration
```python
# Plot Style
plt.style.use('seaborn')

# Figure Sizes
FIGURE_SIZE_STANDARD = (10, 6)
FIGURE_SIZE_WIDE = (15, 8)
FIGURE_SIZE_SQUARE = (10, 10)

# Color Schemes
SENTIMENT_COLORS = {
    'positive': '#2ecc71',
    'neutral': '#95a5a6',
    'negative': '#e74c3c'
}

# Word Cloud Settings
WORDCLOUD_CONFIG = {
    'width': 800,
    'height': 400,
    'background_color': 'white',
    'max_words': 200
}
```

### Output Directory Structure
```
data/analysis/
├── bloomberg/
│   ├── source_distribution.png
│   ├── sentiment_distribution.png
│   └── keyword_wordcloud.png
├── iaea/
│   ├── source_distribution.png
│   ├── sentiment_distribution.png
│   └── keyword_wordcloud.png
└── combined/
    ├── source_distribution.png
    ├── sentiment_distribution.png
    └── keyword_wordcloud.png
```

## Best Practices

### 1. Clarity
- Clear titles and labels
- Appropriate color schemes
- Legend when necessary
- Consistent font sizes

### 2. Accessibility
- Color-blind friendly palettes
- High contrast for text
- Adequate figure sizes
- Clear data labels

### 3. Consistency
- Same style across visualizations
- Consistent color schemes
- Standard figure sizes
- Regular naming conventions

### 4. Interactivity
- Save both static and interactive versions
- Enable zooming for detailed views
- Provide tooltips for data points
- Allow filtering where appropriate

## Usage in Reports

### Markdown Integration
```markdown
## Source Distribution
![Source Distribution](data/analysis/source_distribution.png)

## Sentiment Analysis
![Sentiment Distribution](data/analysis/sentiment_distribution.png)

## Key Topics
![Keyword Cloud](data/analysis/keyword_wordcloud.png)
```

### Interactive Features
- Hover tooltips for detailed information
- Click-through for detailed views
- Filter controls for time periods
- Export options for different formats

## Dependencies
- matplotlib
- seaborn
- wordcloud
- plotly (for interactive versions)

## Future Enhancements
1. Interactive dashboards
2. Real-time updating visualizations
3. Custom color schemes
4. Additional chart types
5. Export to multiple formats
