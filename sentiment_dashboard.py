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

# Download necessary NLTK resources
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

# Connect to the database
DATABASE_PATH = "data/db/IAEA.db"

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

def analyze_sentiment(text):
    """Analyze sentiment of text using TextBlob"""
    if pd.isna(text) or text == '':
        return {'polarity': 0, 'subjectivity': 0}
    
    # Clean text
    text = re.sub(r'[^a-zA-Z\s]', '', text, re.UNICODE)
    
    # Analyze sentiment
    blob = TextBlob(text)
    
    return {
        'polarity': blob.sentiment.polarity,
        'subjectivity': blob.sentiment.subjectivity
    }

def generate_sentiment_analysis(df):
    """Apply sentiment analysis to title and content"""
    # Analyze sentiment for title and content
    title_sentiments = df['title'].apply(analyze_sentiment)
    content_sentiments = df['content'].apply(analyze_sentiment)
    
    # Extract polarities and subjectivities
    df['title_polarity'] = [sentiment['polarity'] for sentiment in title_sentiments]
    df['title_subjectivity'] = [sentiment['subjectivity'] for sentiment in title_sentiments]
    df['content_polarity'] = [sentiment['polarity'] for sentiment in content_sentiments]
    df['content_subjectivity'] = [sentiment['subjectivity'] for sentiment in content_sentiments]
    
    # Calculate overall sentiment
    df['overall_polarity'] = (df['title_polarity'] + df['content_polarity']) / 2
    df['overall_subjectivity'] = (df['title_subjectivity'] + df['content_subjectivity']) / 2
    
    # Categorize sentiment
    df['sentiment_category'] = pd.cut(
        df['overall_polarity'],
        bins=[-1, -0.3, 0.3, 1],
        labels=['Negative', 'Neutral', 'Positive']
    )
    
    return df

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
        'overall_subjectivity': 'mean',
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
        name='Sentiment Polarity',
        line=dict(color='blue', width=2),
        marker=dict(size=8),
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
            title='Sentiment Polarity',
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
            'green' if x > 0.3 else 'red' if x < -0.3 else 'gray'
            for x in type_sentiment['overall_polarity']
        ],
        name='Avg. Sentiment'
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
            title='Average Sentiment Polarity',
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

def plot_subjectivity_vs_polarity(df):
    """Create scatter plot of subjectivity vs polarity"""
    # Create figure
    fig = px.scatter(
        df,
        x='overall_subjectivity',
        y='overall_polarity',
        color='sentiment_category',
        color_discrete_map={
            'Negative': 'red',
            'Neutral': 'gray',
            'Positive': 'green'
        },
        hover_data=['title'],
        title='Subjectivity vs. Polarity',
        opacity=0.7
    )
    
    # Add quadrant lines
    fig.add_hline(y=0, line_dash='dash', line_color='gray')
    fig.add_vline(x=0.5, line_dash='dash', line_color='gray')
    
    # Update layout
    fig.update_layout(
        xaxis_title='Subjectivity (Objective → Subjective)',
        yaxis_title='Polarity (Negative → Positive)',
        xaxis=dict(range=[0, 1]),
        yaxis=dict(range=[-1, 1]),
        template='plotly_white'
    )
    
    # Add annotations for quadrants
    fig.add_annotation(x=0.25, y=0.5, text="Objective Positive", showarrow=False)
    fig.add_annotation(x=0.75, y=0.5, text="Subjective Positive", showarrow=False)
    fig.add_annotation(x=0.25, y=-0.5, text="Objective Negative", showarrow=False)
    fig.add_annotation(x=0.75, y=-0.5, text="Subjective Negative", showarrow=False)
    
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
        gr.Markdown("This dashboard analyzes sentiment patterns in IAEA news articles.")
        
        with gr.Tabs():
            with gr.TabItem("Overview"):
                with gr.Row():
                    with gr.Column():
                        # Summary statistics
                        total_articles = len(df)
                        avg_polarity = df['overall_polarity'].mean()
                        sentiment_counts = df['sentiment_category'].value_counts()
                        positive_pct = sentiment_counts.get('Positive', 0) / total_articles * 100
                        negative_pct = sentiment_counts.get('Negative', 0) / total_articles * 100
                        neutral_pct = sentiment_counts.get('Neutral', 0) / total_articles * 100
                        
                        stats_md = f"""
                        ## Summary Statistics
                        - **Total Articles**: {total_articles}
                        - **Average Sentiment**: {avg_polarity:.2f}
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
                
                gr.Markdown("### Subjectivity vs. Polarity")
                scatter_plot = gr.Plot(value=plot_subjectivity_vs_polarity(df))
            
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
    dashboard.launch(share=False)
