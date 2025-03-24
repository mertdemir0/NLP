import sqlite3
import pandas as pd
import nltk
import re
from textblob import TextBlob
import gradio as gr
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import numpy as np
import io
import base64
from PIL import Image
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from collections import Counter

# Download necessary NLTK resources
print("Downloading NLTK resources...")
nltk.download('vader_lexicon', quiet=False)
nltk.download('stopwords', quiet=False)
print("NLTK resources downloaded successfully")

# Connect to the database
DATABASE_PATH = "data/db/IAEA.db"

# Nuclear domain specific terms and their sentiment adjustments
NUCLEAR_DOMAIN_TERMS = {
    # Positive terms in nuclear context
    'safety': 1.5,
    'secure': 1.5,
    'peaceful': 2.0,
    'sustainable': 1.5,
    'clean': 1.5,
    'renewable': 1.2,
    'cooperation': 1.5,
    'agreement': 1.2,
    'development': 1.0,
    'progress': 1.2,
    'innovation': 1.5,
    'advanced': 1.2,
    'improvement': 1.5,
    'success': 1.5,
    'achievement': 1.5,
    'benefit': 1.5,
    'solution': 1.2,
    
    # Negative terms in nuclear context
    'radiation': -1.0,  # Neutral in nuclear context
    'waste': -1.2,
    'leak': -2.0,
    'contamination': -2.0,
    'accident': -2.0,
    'disaster': -2.5,
    'crisis': -2.0,
    'risk': -1.2,
    'concern': -1.0,
    'problem': -1.2,
    'danger': -1.8,
    'threat': -1.8,
    'emergency': -1.5,
    'incident': -1.5,
    'proliferation': -1.8,
    'weapon': -1.5,
    'attack': -2.0,
    'explosion': -2.0,
    'meltdown': -2.5,
    'failure': -1.8,
    'violation': -1.8,
}

def load_data():
    """Load data from the IAEA database"""
    conn = sqlite3.connect(DATABASE_PATH)
    query = "SELECT id, title, content, date, type FROM IAEA"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Clean up data
    df['content'] = df['content'].fillna('')
    df['title'] = df['title'].fillna('')
    
    # Extract year and month from date
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    
    return df

def preprocess_text(text):
    """Preprocess text for sentiment analysis"""
    if pd.isna(text) or text == '':
        return ''
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    
    # Remove HTML tags
    text = re.sub(r'<.*?>', '', text)
    
    # Remove special characters and numbers (preserve negations like "not" and "no")
    text = re.sub(r'[^a-zA-Z\s\'not\sno]', ' ', text)
    
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def simple_tokenize(text):
    """Simple tokenization without relying on NLTK's punkt"""
    if not text:
        return []
    # Split by whitespace and remove empty strings
    return [word for word in text.split() if word]

def analyze_sentiment_with_domain_knowledge(text, sia=None):
    """
    Analyze sentiment with domain knowledge enhancement
    using both VADER and TextBlob for better accuracy
    """
    if pd.isna(text) or text == '':
        return {'compound': 0, 'pos': 0, 'neu': 0, 'neg': 0, 'textblob': 0}
    
    # Preprocess the text
    processed_text = preprocess_text(text)
    if not processed_text:
        return {'compound': 0, 'pos': 0, 'neu': 0, 'neg': 0, 'textblob': 0}
    
    # Initialize VADER analyzer if not provided
    if sia is None:
        sia = SentimentIntensityAnalyzer()
    
    # Get base VADER sentiment
    vader_scores = sia.polarity_scores(processed_text)
    
    # Get TextBlob sentiment
    blob = TextBlob(processed_text)
    textblob_polarity = blob.sentiment.polarity
    
    # Apply domain-specific adjustments
    words = simple_tokenize(processed_text)
    domain_score = 0
    match_count = 0
    
    for word in words:
        if word in NUCLEAR_DOMAIN_TERMS:
            domain_score += NUCLEAR_DOMAIN_TERMS[word]
            match_count += 1
    
    # Normalize domain score
    if match_count > 0:
        domain_score = domain_score / match_count
        # Adjust the compound score with domain knowledge (70% original, 30% domain)
        vader_scores['compound'] = 0.7 * vader_scores['compound'] + 0.3 * (domain_score / 2.5)  # Normalize to [-1, 1]
    
    # Combine VADER and TextBlob (60% VADER, 40% TextBlob)
    combined_score = 0.6 * vader_scores['compound'] + 0.4 * textblob_polarity
    
    # Ensure the score is within [-1, 1]
    combined_score = max(-1, min(1, combined_score))
    
    # Update the compound score
    vader_scores['compound'] = combined_score
    vader_scores['textblob'] = textblob_polarity
    
    return vader_scores

def generate_sentiment_analysis(df):
    """Apply enhanced sentiment analysis to title and content"""
    # Initialize VADER analyzer (reuse for efficiency)
    sia = SentimentIntensityAnalyzer()
    
    # Analyze sentiment for title and content
    title_sentiments = df['title'].apply(lambda x: analyze_sentiment_with_domain_knowledge(x, sia))
    content_sentiments = df['content'].apply(lambda x: analyze_sentiment_with_domain_knowledge(x, sia))
    
    # Extract sentiments
    df['title_polarity'] = [sentiment['compound'] for sentiment in title_sentiments]
    df['title_pos'] = [sentiment['pos'] for sentiment in title_sentiments]
    df['title_neu'] = [sentiment['neu'] for sentiment in title_sentiments]
    df['title_neg'] = [sentiment['neg'] for sentiment in title_sentiments]
    df['title_textblob'] = [sentiment['textblob'] for sentiment in title_sentiments]
    
    df['content_polarity'] = [sentiment['compound'] for sentiment in content_sentiments]
    df['content_pos'] = [sentiment['pos'] for sentiment in content_sentiments]
    df['content_neu'] = [sentiment['neu'] for sentiment in content_sentiments]
    df['content_neg'] = [sentiment['neg'] for sentiment in content_sentiments]
    df['content_textblob'] = [sentiment['textblob'] for sentiment in content_sentiments]
    
    # Calculate overall sentiment
    # Title gets more weight (30%) as it's often more indicative of sentiment in news articles
    df['overall_polarity'] = df['title_polarity'] * 0.3 + df['content_polarity'] * 0.7
    
    # Calculate sentiment metrics
    df['positivity'] = df['title_pos'] * 0.3 + df['content_pos'] * 0.7
    df['negativity'] = df['title_neg'] * 0.3 + df['content_neg'] * 0.7
    df['neutrality'] = df['title_neu'] * 0.3 + df['content_neu'] * 0.7
    
    # Categorize sentiment with improved thresholds (adjusted for nuclear domain)
    df['sentiment_category'] = pd.cut(
        df['overall_polarity'],
        bins=[-1, -0.1, 0.1, 1],
        labels=['Negative', 'Neutral', 'Positive']
    )
    
    # Extract key terms and their sentiment contribution
    df['key_terms'] = df['content'].apply(extract_key_terms)
    
    return df

def extract_key_terms(text, top_n=5):
    """Extract key terms that contribute to sentiment"""
    if pd.isna(text) or text == '':
        return []
    
    processed_text = preprocess_text(text)
    words = simple_tokenize(processed_text)
    
    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Count occurrences
    word_counts = Counter(filtered_words)
    
    # Get domain-specific terms
    domain_terms = []
    for word in word_counts:
        if word in NUCLEAR_DOMAIN_TERMS:
            domain_terms.append((word, word_counts[word], NUCLEAR_DOMAIN_TERMS[word]))
    
    # Sort by absolute sentiment value and count
    domain_terms.sort(key=lambda x: (abs(x[2]), x[1]), reverse=True)
    
    # Return top terms
    return domain_terms[:top_n]

def create_wordcloud(df, sentiment_filter=None):
    """Create wordcloud based on sentiment filter"""
    if sentiment_filter:
        filtered_df = df[df['sentiment_category'] == sentiment_filter]
    else:
        filtered_df = df
    
    all_text = ' '.join([
        ' '.join([str(title), str(content)]) 
        for title, content in zip(filtered_df['title'], filtered_df['content'])
        if not pd.isna(title) and not pd.isna(content)
    ])
    
    stopwords = set(nltk.corpus.stopwords.words('english'))
    stopwords.update(['said', 'also', 'would', 'could', 'one', 'may', 'many'])
    
    # Generate wordcloud
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color='white',
        stopwords=stopwords,
        max_words=100
    ).generate(all_text)
    
    # Convert to image
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    
    # Save to bytes
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    # Convert to base64
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return f"data:image/png;base64,{img_str}"

def plot_sentiment_over_time(df):
    """Plot sentiment over time"""
    # Group by date and calculate average sentiment
    time_df = df.groupby(['year', 'month']).agg({
        'overall_polarity': 'mean',
        'positivity': 'mean',
        'negativity': 'mean',
        'id': 'count'
    }).reset_index()
    
    # Create date column for plotting
    time_df['date_str'] = time_df.apply(
        lambda x: f"{int(x['year'])}-{int(x['month']):02d}", 
        axis=1
    )
    
    # Create plotly figure
    fig = go.Figure()
    
    # Add polarity line
    fig.add_trace(go.Scatter(
        x=time_df['date_str'],
        y=time_df['overall_polarity'],
        mode='lines+markers',
        name='Overall Sentiment',
        line=dict(color='blue', width=2),
        marker=dict(size=8),
    ))
    
    # Add positivity line
    fig.add_trace(go.Scatter(
        x=time_df['date_str'],
        y=time_df['positivity'],
        mode='lines+markers',
        name='Positivity',
        line=dict(color='green', width=2),
        marker=dict(size=6),
        visible='legendonly',
    ))
    
    # Add negativity line
    fig.add_trace(go.Scatter(
        x=time_df['date_str'],
        y=time_df['negativity'],
        mode='lines+markers',
        name='Negativity',
        line=dict(color='red', width=2),
        marker=dict(size=6),
        visible='legendonly',
    ))
    
    # Add article count bars
    fig.add_trace(go.Bar(
        x=time_df['date_str'],
        y=time_df['id'],
        name='Article Count',
        marker_color='rgba(0, 128, 0, 0.3)',
        yaxis='y2'
    ))
    
    # Update layout
    fig.update_layout(
        title='Sentiment Analysis Over Time',
        xaxis=dict(title='Date'),
        yaxis=dict(
            title='Sentiment Score',
            titlefont=dict(color='blue'),
            tickfont=dict(color='blue'),
            range=[-1, 1]
        ),
        yaxis2=dict(
            title='Article Count',
            titlefont=dict(color='green'),
            tickfont=dict(color='green'),
            anchor='x',
            overlaying='y',
            side='right'
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        template='plotly_white'
    )
    
    return fig

def plot_sentiment_distribution(df):
    """Plot distribution of sentiment categories"""
    # Count sentiment categories
    sentiment_counts = df['sentiment_category'].value_counts().reset_index()
    sentiment_counts.columns = ['category', 'count']
    
    # Order categories
    category_order = ['Negative', 'Neutral', 'Positive']
    sentiment_counts['category'] = pd.Categorical(
        sentiment_counts['category'], 
        categories=category_order, 
        ordered=True
    )
    sentiment_counts = sentiment_counts.sort_values('category')
    
    # Create colors for each category
    colors = {'Negative': 'red', 'Neutral': 'gray', 'Positive': 'green'}
    bar_colors = [colors[cat] for cat in sentiment_counts['category']]
    
    # Create figure
    fig = px.bar(
        sentiment_counts, 
        x='category', 
        y='count',
        text='count',
        color='category',
        color_discrete_map=colors,
        title='Distribution of Sentiment Categories'
    )
    
    fig.update_layout(
        xaxis_title='Sentiment Category',
        yaxis_title='Count',
        template='plotly_white'
    )
    
    return fig

def plot_type_sentiment(df):
    """Plot sentiment by article type"""
    # Group by type and calculate average sentiment
    type_sentiment = df.groupby('type').agg({
        'overall_polarity': 'mean',
        'positivity': 'mean',
        'negativity': 'mean',
        'id': 'count'
    }).reset_index()
    
    # Sort by count
    type_sentiment = type_sentiment.sort_values('id', ascending=False)
    
    # Create figure
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(go.Bar(
        x=type_sentiment['type'],
        y=type_sentiment['overall_polarity'],
        marker_color=[
            'green' if x > 0.1 else 'red' if x < -0.1 else 'gray'
            for x in type_sentiment['overall_polarity']
        ],
        name='Overall Sentiment'
    ))
    
    # Add positivity bars (stacked)
    fig.add_trace(go.Bar(
        x=type_sentiment['type'],
        y=type_sentiment['positivity'],
        marker_color='rgba(0, 128, 0, 0.6)',
        name='Positivity',
        visible='legendonly'
    ))
    
    # Add negativity bars (stacked)
    fig.add_trace(go.Bar(
        x=type_sentiment['type'],
        y=type_sentiment['negativity'],
        marker_color='rgba(255, 0, 0, 0.6)',
        name='Negativity',
        visible='legendonly'
    ))
    
    # Add article count line
    fig.add_trace(go.Scatter(
        x=type_sentiment['type'],
        y=type_sentiment['id'],
        mode='lines+markers',
        name='Article Count',
        yaxis='y2',
        line=dict(color='blue', width=2),
        marker=dict(size=8)
    ))
    
    # Update layout
    fig.update_layout(
        title='Sentiment Analysis by Article Type',
        xaxis=dict(title='Article Type'),
        yaxis=dict(
            title='Sentiment Score',
            range=[-1, 1]
        ),
        yaxis2=dict(
            title='Article Count',
            titlefont=dict(color='blue'),
            tickfont=dict(color='blue'),
            anchor='x',
            overlaying='y',
            side='right'
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        template='plotly_white'
    )
    
    return fig

def plot_key_terms_impact(df):
    """Plot impact of key terms on sentiment"""
    # Extract key terms with their sentiment impact
    all_terms = []
    for _, row in df.iterrows():
        for term in row['key_terms']:
            all_terms.append({
                'term': term[0],
                'count': term[1],
                'sentiment_impact': term[2]
            })
    
    # Create DataFrame of terms
    if not all_terms:
        return go.Figure()  # Return empty figure if no terms
    
    terms_df = pd.DataFrame(all_terms)
    
    # Aggregate by term
    terms_agg = terms_df.groupby('term').agg({
        'count': 'sum',
        'sentiment_impact': 'mean'
    }).reset_index()
    
    # Sort by impact and count
    terms_agg = terms_agg.sort_values(['count', 'sentiment_impact'], ascending=[False, False])
    
    # Take top terms
    top_terms = terms_agg.head(15)
    
    # Create figure
    fig = px.scatter(
        top_terms,
        x='sentiment_impact',
        y='count',
        text='term',
        size='count',
        color='sentiment_impact',
        color_continuous_scale=['red', 'gray', 'green'],
        range_color=[-2.5, 2.5],
        title='Key Terms Impact on Sentiment',
    )
    
    # Update layout
    fig.update_traces(
        textposition='top center',
        marker=dict(sizemode='area', sizeref=0.1)
    )
    
    fig.update_layout(
        xaxis_title='Sentiment Impact',
        yaxis_title='Frequency',
        template='plotly_white'
    )
    
    return fig

def search_articles(df, keyword):
    """Search articles containing the keyword"""
    if not keyword:
        return pd.DataFrame()
    
    # Search in title and content
    mask = (
        df['title'].str.contains(keyword, case=False, na=False) | 
        df['content'].str.contains(keyword, case=False, na=False)
    )
    
    return df[mask][['title', 'date', 'type', 'overall_polarity', 'sentiment_category']]

def create_dashboard():
    """Create Gradio dashboard"""
    # Load and analyze data
    df = load_data()
    df = generate_sentiment_analysis(df)
    
    # Create dashboard interface
    with gr.Blocks(title="IAEA News Sentiment Analysis Dashboard") as dashboard:
        gr.Markdown("# IAEA News Sentiment Analysis Dashboard")
        gr.Markdown("This dashboard analyzes sentiment patterns in IAEA news articles with domain-specific enhancements for nuclear energy content.")
        
        with gr.Tabs():
            with gr.TabItem("Overview"):
                with gr.Row():
                    with gr.Column():
                        # Summary statistics
                        total_articles = len(df)
                        avg_polarity = df['overall_polarity'].mean()
                        avg_positivity = df['positivity'].mean()
                        avg_negativity = df['negativity'].mean()
                        sentiment_counts = df['sentiment_category'].value_counts()
                        positive_pct = sentiment_counts.get('Positive', 0) / total_articles * 100
                        negative_pct = sentiment_counts.get('Negative', 0) / total_articles * 100
                        neutral_pct = sentiment_counts.get('Neutral', 0) / total_articles * 100
                        
                        stats_md = f"""
                        ## Summary Statistics
                        - **Total Articles**: {total_articles}
                        - **Average Sentiment Score**: {avg_polarity:.3f}
                        - **Average Positivity**: {avg_positivity:.3f}
                        - **Average Negativity**: {avg_negativity:.3f}
                        - **Sentiment Distribution**:
                          - Positive: {positive_pct:.1f}%
                          - Neutral: {neutral_pct:.1f}%
                          - Negative: {negative_pct:.1f}%
                        """
                        gr.Markdown(stats_md)
                        
                    with gr.Column():
                        distribution_plot = gr.Plot(value=plot_sentiment_distribution(df))
                
                gr.Markdown("### Sentiment Over Time")
                time_plot = gr.Plot(value=plot_sentiment_over_time(df))
                
                gr.Markdown("### Word Cloud (All Articles)")
                wordcloud_all = gr.HTML(value=f'<img src="{create_wordcloud(df)}" width="100%"/>')
                
                gr.Markdown("### Key Terms Impact on Sentiment")
                terms_plot = gr.Plot(value=plot_key_terms_impact(df))
            
            with gr.TabItem("By Category"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Positive Articles Word Cloud")
                        wordcloud_pos = gr.HTML(value=f'<img src="{create_wordcloud(df, "Positive")}" width="100%"/>')
                    
                    with gr.Column():
                        gr.Markdown("### Negative Articles Word Cloud")
                        wordcloud_neg = gr.HTML(value=f'<img src="{create_wordcloud(df, "Negative")}" width="100%"/>')
                
                gr.Markdown("### Sentiment by Article Type")
                type_plot = gr.Plot(value=plot_type_sentiment(df))
            
            with gr.TabItem("Article Search"):
                with gr.Row():
                    search_input = gr.Textbox(label="Search Articles")
                    search_button = gr.Button("Search")
                
                search_results = gr.DataFrame(
                    headers=["Title", "Date", "Type", "Sentiment Score", "Sentiment Category"],
                    value=pd.DataFrame()
                )
                
                search_button.click(
                    fn=lambda keyword: search_articles(df, keyword).values.tolist(),
                    inputs=search_input,
                    outputs=search_results
                )
    
    return dashboard

if __name__ == "__main__":
    dashboard = create_dashboard()
    dashboard.launch(share=True)