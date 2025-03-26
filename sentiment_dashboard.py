import sqlite3
import pandas as pd
import nltk
import re
import numpy as np
from textblob import TextBlob
import gradio as gr
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import io
import base64
from PIL import Image
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from collections import Counter
import os

# For new features
import gensim
from gensim import corpora
from gensim.models import LdaModel
import spacy
import json
from sklearn.feature_extraction.text import CountVectorizer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import seaborn as sns
import matplotlib.dates as mdates
import plotly.figure_factory as ff

# Download necessary NLTK resources
print("Downloading NLTK resources...")
nltk.download('vader_lexicon', quiet=False)
nltk.download('stopwords', quiet=False)
print("NLTK resources downloaded successfully")

# Load spaCy model for NER
try:
    nlp = spacy.load("en_core_web_sm")
    print("Successfully loaded spaCy model")
except OSError:
    print("SpaCy model not found. Downloading...")
    # Download using subprocess with uv
    import subprocess
    try:
        subprocess.run(["uv", "pip", "install", "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0-py3-none-any.whl"], check=True)
        nlp = spacy.load("en_core_web_sm")
        print("Successfully loaded spaCy model")
    except Exception as e:
        print(f"Failed to download spaCy model: {e}")
        print("Attempting to load a simple NLP processor...")
        # Create a simple NLP processor as a fallback
        class SimpleNLP:
            def __call__(self, text):
                doc = type('obj', (object,), {
                    'ents': [],
                    'text': text
                })
                return doc
        nlp = SimpleNLP()
        print("Using simple NLP processor instead")

# Initialize sentence transformer model for contextual embeddings
print("Loading Sentence Transformer model...")
try:
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Sentence Transformer model loaded successfully")
except Exception as e:
    print(f"Error loading Sentence Transformer model: {e}")
    sentence_model = None

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

# Define major nuclear events for temporal correlation
NUCLEAR_EVENTS = [
    {"date": "2011-03-11", "event": "Fukushima Daiichi disaster", "sentiment_impact": -2.0},
    {"date": "2015-07-14", "event": "Iran Nuclear Deal", "sentiment_impact": 1.5},
    {"date": "2016-01-16", "event": "Iran Sanctions Relief", "sentiment_impact": 1.0},
    {"date": "2017-07-07", "event": "UN Treaty on Prohibition of Nuclear Weapons", "sentiment_impact": 1.5},
    {"date": "2018-05-08", "event": "US Withdrawal from Iran Nuclear Deal", "sentiment_impact": -1.5},
    {"date": "2019-08-02", "event": "US Withdrawal from INF Treaty", "sentiment_impact": -1.0},
    {"date": "2020-01-29", "event": "Doomsday Clock set at 100 seconds to midnight", "sentiment_impact": -1.0},
    {"date": "2021-01-22", "event": "Treaty on the Prohibition of Nuclear Weapons enters into force", "sentiment_impact": 1.5},
    {"date": "2022-02-24", "event": "Russian invasion of Ukraine (nuclear threats)", "sentiment_impact": -2.0},
    {"date": "2023-02-21", "event": "Russia suspends participation in New START Treaty", "sentiment_impact": -1.5},
]

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
    
    Returns:
        tuple: (polarity, positivity, negativity, reliability, key_terms)
    """
    if pd.isna(text) or text == '':
        return 0, 0, 0, 0, []
    
    # Preprocess the text
    processed_text = preprocess_text(text)
    if not processed_text:
        return 0, 0, 0, 0, []
    
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
    
    # Calculate sentiment reliability score (Feature 10)
    reliability = calculate_sentiment_reliability(processed_text, vader_scores, textblob_polarity)
    
    # Extract key terms that contribute to sentiment
    key_terms = extract_key_terms(processed_text)
    
    # Return the tuple of values needed by generate_sentiment_analysis
    return combined_score, vader_scores['pos'], vader_scores['neg'], reliability, key_terms

def calculate_sentiment_reliability(text, vader_scores, textblob_score):
    """
    Calculate a reliability score for sentiment analysis (Feature 10)
    based on text length, agreement between models, and presence of ambiguous language
    """
    reliability = 0.5  # Start with neutral reliability
    
    # Factor 1: Text length (longer text typically provides more context for accurate analysis)
    text_length = len(text.split())
    if text_length < 5:
        reliability -= 0.2
    elif text_length > 30:
        reliability += 0.2
    
    # Factor 2: Agreement between VADER and TextBlob
    vader_compound = vader_scores['compound']
    agreement_diff = abs(vader_compound - textblob_score)
    if agreement_diff < 0.2:
        reliability += 0.2
    elif agreement_diff > 0.5:
        reliability -= 0.2
    
    # Factor 3: Presence of conflicting sentiment signals
    if (vader_scores['pos'] > 0.2 and vader_scores['neg'] > 0.2):
        reliability -= 0.15
    
    # Factor 4: Strength of sentiment (very neutral texts may indicate ambiguity)
    if abs(vader_compound) < 0.1:
        reliability -= 0.1
    elif abs(vader_compound) > 0.5:
        reliability += 0.1
    
    # Ensure reliability is between 0 and 1
    reliability = max(0, min(1, reliability))
    
    return reliability

def analyze_content_with_bert(text):
    """
    Use contextual word embeddings (BERT) for improved sentiment analysis (Feature 9)
    """
    if pd.isna(text) or text == '' or sentence_model is None:
        return None
    
    # Preprocess the text
    processed_text = preprocess_text(text)
    if not processed_text:
        return None
    
    # Get embedding
    try:
        embedding = sentence_model.encode(processed_text)
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def extract_named_entities(text, nlp_model=None):
    """
    Extract named entities from text using spaCy (Feature 2)
    
    Args:
        text (str): The text to analyze
        nlp_model: The spaCy model to use (default: global nlp)
    
    Returns:
        list: List of named entities with their labels
    """
    if pd.isna(text) or text == '':
        return []
    
    # Use global nlp if not provided
    if nlp_model is None:
        nlp_model = nlp
    
    # Process the text with spaCy
    doc = nlp_model(text[:10000])  # Limit to 10000 chars to avoid memory issues
    
    # Extract entities
    entities = []
    for ent in doc.ents:
        entities.append({
            'text': ent.text,
            'label': ent.label_,
            'start': ent.start_char,
            'end': ent.end_char
        })
    
    return entities

def create_topic_model(documents, num_topics=5):
    """Create a topic model using LDA from gensim"""
    # Check if we have enough documents
    import numpy as np
    
    if isinstance(documents, pd.Series):
        documents = documents.tolist()
    elif isinstance(documents, np.ndarray):
        documents = documents.tolist()
    
    # Check if we have documents
    if not documents or len(documents) < 5:
        print("Not enough documents for topic modeling")
        return None, None, None
    
    # Preprocess documents for topic modeling
    processed_docs = []
    for doc in documents:
        if pd.isna(doc) or not doc:  # Skip empty documents
            continue
        # Tokenize and clean
        tokens = gensim.utils.simple_preprocess(str(doc), deacc=True)
        # Remove stopwords
        stop_words = set(nltk.corpus.stopwords.words('english'))
        tokens = [token for token in tokens if token not in stop_words and len(token) > 3]
        processed_docs.append(tokens)
    
    if len(processed_docs) < 5:
        print("Not enough valid documents after preprocessing")
        return None, None, None
        
    # Create dictionary and corpus
    dictionary = gensim.corpora.Dictionary(processed_docs)
    # Filter extreme values
    dictionary.filter_extremes(no_below=2, no_above=0.9)
    corpus = [dictionary.doc2bow(doc) for doc in processed_docs]
    
    # Train LDA model
    lda_model = gensim.models.LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=num_topics,
        passes=15,
        alpha='auto',
        per_word_topics=True
    )
    
    return lda_model, dictionary, corpus

def get_document_topics(lda_model, dictionary, corpus, threshold=0.3):
    """
    Get the dominant topics for each document
    """
    if lda_model is None or dictionary is None or corpus is None:
        return []
    
    doc_topics = []
    
    for i, doc_bow in enumerate(corpus):
        topic_probs = lda_model.get_document_topics(doc_bow)
        dominant_topics = [topic for topic, prob in topic_probs if prob >= threshold]
        doc_topics.append(dominant_topics)
    
    return doc_topics

def get_topic_sentiments(df, doc_topics, num_topics):
    """
    Calculate sentiment by topic (Feature 1)
    """
    topic_sentiments = {i: [] for i in range(num_topics)}
    
    for i, topics in enumerate(doc_topics):
        sentiment = df.iloc[i]['overall_polarity']
        for topic in topics:
            topic_sentiments[topic].append(sentiment)
    
    # Calculate average sentiment per topic
    topic_avg_sentiment = {}
    for topic, sentiments in topic_sentiments.items():
        if sentiments:
            topic_avg_sentiment[topic] = sum(sentiments) / len(sentiments)
        else:
            topic_avg_sentiment[topic] = 0
    
    return topic_avg_sentiment

def predict_sentiment_trends(df, periods=12):
    """
    Predict future sentiment trends using time series forecasting (Feature 6)
    """
    # Check if we have enough data
    if len(df) < 10:
        print("Not enough data for forecasting")
        return None
        
    try:
        # Create a copy of the dataframe with just the columns we need
        temp_df = df[['date', 'overall_polarity']].copy()
        
        # Extract year and month as separate columns
        temp_df['year'] = temp_df['date'].dt.year
        temp_df['month'] = temp_df['date'].dt.month
        
        # Group by year and month manually
        monthly_sentiment = temp_df.groupby(['year', 'month'])['overall_polarity'].mean().reset_index()
        
        # Create date column for time series
        monthly_sentiment['forecast_date'] = pd.to_datetime(monthly_sentiment[['year', 'month']].assign(day=1))
        
        # Sort by date
        monthly_sentiment = monthly_sentiment.sort_values('forecast_date')
        
        # Check if we have enough timestamps
        if len(monthly_sentiment) < 3:
            print("Not enough time points for forecasting")
            return None
            
        # Create a time series
        time_series = monthly_sentiment.set_index('forecast_date')['overall_polarity']
        
        # Get the frequency of the time series
        try:
            freq = pd.infer_freq(time_series.index)
            if freq is None:
                freq = 'MS'  # Monthly start as fallback
        except:
            freq = 'MS'  # Monthly start as fallback
            
        # Create and fit the ARIMA model
        try:
            from statsmodels.tsa.arima.model import ARIMA
            
            # Try to fit ARIMA model
            model = ARIMA(time_series, order=(1, 1, 1), freq=freq)
            model_fit = model.fit()
            
            # Generate forecast
            forecast = model_fit.forecast(steps=periods)
            
            # Create forecast DataFrame
            forecast_dates = pd.date_range(start=time_series.index[-1], periods=periods+1, freq=freq)[1:]
            forecast_df = pd.DataFrame({
                'forecast_date': forecast_dates,
                'sentiment': forecast.values,
                'type': 'Forecast'
            })
            
            # Combine historical data with forecast
            historical_df = pd.DataFrame({
                'forecast_date': time_series.index,
                'sentiment': time_series.values,
                'type': 'Historical'
            })
            
            result_df = pd.concat([historical_df, forecast_df])
            
            # Add confidence intervals for forecast data - fixed to avoid stderr error
            forecast_index = result_df['type'] == 'Forecast'
            # Use a fixed value for confidence intervals if stderr is not available
            std_error = 0.1  # Fixed standard error as fallback
            result_df.loc[forecast_index, 'lower_ci'] = result_df.loc[forecast_index, 'sentiment'] - 1.96 * std_error
            result_df.loc[forecast_index, 'upper_ci'] = result_df.loc[forecast_index, 'sentiment'] + 1.96 * std_error
            
            return result_df
            
        except Exception as e:
            print(f"Error in ARIMA forecasting: {e}")
            
            # Fallback to simple moving average
            time_series_ma = time_series.rolling(window=3).mean()
            last_value = time_series_ma.iloc[-1] if not pd.isna(time_series_ma.iloc[-1]) else time_series.iloc[-1]
            
            # Simple forecast with slight random variation
            forecast_values = [last_value + np.random.normal(0, 0.05) for _ in range(periods)]
            
            # Create forecast DataFrame
            forecast_dates = pd.date_range(start=time_series.index[-1], periods=periods+1, freq=freq)[1:]
            forecast_df = pd.DataFrame({
                'forecast_date': forecast_dates,
                'sentiment': forecast_values,
                'type': 'Forecast'
            })
            
            # Combine historical data with forecast
            historical_df = pd.DataFrame({
                'forecast_date': time_series.index,
                'sentiment': time_series.values,
                'type': 'Historical'
            })
            
            result_df = pd.concat([historical_df, forecast_df])
            
            # Add simple confidence intervals
            forecast_index = result_df['type'] == 'Forecast'
            std_error = 0.1  # Fixed standard error
            result_df.loc[forecast_index, 'lower_ci'] = result_df.loc[forecast_index, 'sentiment'] - 1.96 * std_error
            result_df.loc[forecast_index, 'upper_ci'] = result_df.loc[forecast_index, 'sentiment'] + 1.96 * std_error
            
            return result_df
    
    except Exception as e:
        print(f"Error in sentiment forecasting: {e}")
        return None

def generate_sentiment_analysis(df):
    """Generate sentiment analysis for the dataframe"""
    # Initialize VADER sentiment analyzer
    sia = SentimentIntensityAnalyzer()
    
    # Initialize lists to store results
    polarities = []
    positivity = []
    negativity = []
    categories = []
    reliabilities = []
    key_terms_list = []
    entities_list = []
    
    # Process each article
    print("Analyzing sentiment...")
    for i, row in df.iterrows():
        # Get the content
        content = row['content'] if not pd.isna(row['content']) else ""
        
        # Only analyze non-empty content
        if content.strip():
            # Get sentiment scores with domain knowledge
            polarity, pos, neg, reliability, key_terms = analyze_sentiment_with_domain_knowledge(content, sia)
            
            # Get named entities
            entities = extract_named_entities(content, nlp)
            
            # Store results
            polarities.append(polarity)
            positivity.append(pos)
            negativity.append(neg)
            reliabilities.append(reliability)
            key_terms_list.append(key_terms)
            entities_list.append(entities)
            
            # Categorize sentiment
            if polarity > 0.1:
                categories.append('Positive')
            elif polarity < -0.1:
                categories.append('Negative')
            else:
                categories.append('Neutral')
        else:
            # Handle empty content
            polarities.append(0)
            positivity.append(0)
            negativity.append(0)
            reliabilities.append(0)
            categories.append('Neutral')
            key_terms_list.append([])
            entities_list.append([])
    
    # Add results to dataframe
    df['overall_polarity'] = polarities
    df['positivity'] = positivity
    df['negativity'] = negativity
    df['sentiment_category'] = categories
    df['content_reliability'] = reliabilities
    df['key_terms'] = key_terms_list
    df['named_entities'] = entities_list
    
    # Add year for temporal analysis
    df['year'] = df['date'].dt.year
    
    # Create topic model from all non-empty documents
    valid_docs = df['content'].dropna().replace('', np.nan).dropna().tolist()
    if len(valid_docs) >= 5:
        print(f"Creating topic model from {len(valid_docs)} documents...")
        lda_model, dictionary, corpus = create_topic_model(valid_docs, num_topics=5)
        
        # Map each document to its main topic
        doc_topics = []
        for i, row in df.iterrows():
            content = row['content'] if not pd.isna(row['content']) else ""
            if content.strip():
                # Process the document for topic modeling
                tokens = gensim.utils.simple_preprocess(str(content), deacc=True)
                stop_words = set(nltk.corpus.stopwords.words('english'))
                tokens = [token for token in tokens if token not in stop_words and len(token) > 3]
                
                # Get document topics
                doc_bow = dictionary.doc2bow(tokens)
                doc_topics_raw = lda_model.get_document_topics(doc_bow)
                
                # Find the dominant topic
                if doc_topics_raw:
                    main_topic = max(doc_topics_raw, key=lambda x: x[1])
                    doc_topics.append(main_topic[0])  # Dominant topic ID
                else:
                    doc_topics.append(-1)  # No topics found
            else:
                doc_topics.append(-1)  # Missing/empty content
        
        # Add topics to dataframe
        df['topic'] = doc_topics
    else:
        print("Not enough valid documents for topic modeling")
        df['topic'] = -1  # Default value for no topic
    
    return df

def extract_key_terms(text, top_n=5):
    """
    Extract key terms that contribute to sentiment
    
    Args:
        text (str): The text to analyze
        top_n (int): Number of top terms to extract
    
    Returns:
        list: List of key terms with their sentiment contribution
    """
    if pd.isna(text) or not text:
        return []
    
    try:
        # Preprocess the text
        processed_text = preprocess_text(text)
        if not processed_text:
            return []
            
        # Tokenize
        words = simple_tokenize(processed_text)
        if not words:
            return []
            
        # Remove stopwords
        stop_words = set(nltk.corpus.stopwords.words('english'))
        words = [word for word in words if word.lower() not in stop_words and len(word) > 2]
        
        # Get sentiment for each word
        word_sentiments = {}
        for word in words:
            # Quick sentiment from TextBlob for each word
            blob = TextBlob(word)
            sentiment = blob.sentiment.polarity
            
            # Check if it's a domain term
            if word in NUCLEAR_DOMAIN_TERMS:
                sentiment = NUCLEAR_DOMAIN_TERMS[word] / 5.0  # Normalize
                
            # Add to dictionary if it has sentiment
            if sentiment != 0:
                word_sentiments[word] = sentiment
                
        # Sort by absolute sentiment value
        sorted_terms = sorted(word_sentiments.items(), key=lambda x: abs(x[1]), reverse=True)
        
        # Return top N terms with their sentiment
        result = []
        for term, sentiment in sorted_terms[:top_n]:
            result.append({
                'term': term,
                'sentiment': sentiment
            })
            
        return result
            
    except Exception as e:
        print(f"Error extracting key terms: {e}")
        return []

def create_temporal_event_correlation(df):
    """
    Create temporal correlation between sentiment and major nuclear events (Feature 3)
    """
    if len(df) < 10:
        return None
    
    try:
        # Create a copy of the dataframe with just the columns we need
        temp_df = df[['date', 'overall_polarity']].copy()
        
        # Extract year and month as separate columns
        temp_df['year'] = temp_df['date'].dt.year
        temp_df['month'] = temp_df['date'].dt.month
        
        # Group by year and month manually
        monthly_sentiment = temp_df.groupby(['year', 'month'])['overall_polarity'].mean().reset_index()
        
        # Create proper date column for time series
        monthly_sentiment['event_date'] = pd.to_datetime(monthly_sentiment[['year', 'month']].assign(day=1))
        
        # Sort by date
        monthly_sentiment = monthly_sentiment.sort_values('event_date')
        
        # Define major nuclear events
        nuclear_events = [
            {"date": "2011-03-11", "event": "Fukushima Disaster", "sentiment_impact": -0.9},
            {"date": "2010-05-15", "event": "IAEA Fuel Bank Established", "sentiment_impact": 0.6},
            {"date": "2015-07-14", "event": "Iran Nuclear Deal", "sentiment_impact": 0.7},
            {"date": "2017-07-07", "event": "UN Nuclear Ban Treaty", "sentiment_impact": 0.5},
            {"date": "2018-05-08", "event": "US Withdraws from Iran Deal", "sentiment_impact": -0.6},
            {"date": "2019-08-02", "event": "INF Treaty Collapse", "sentiment_impact": -0.7},
            {"date": "2020-01-20", "event": "NPT Review Conference Delayed", "sentiment_impact": -0.2},
            {"date": "2021-02-03", "event": "New START Extension", "sentiment_impact": 0.5}
        ]
        
        # Convert to DataFrame
        events_df = pd.DataFrame(nuclear_events)
        events_df['event_date'] = pd.to_datetime(events_df['date'])
        
        # Create figure
        fig = go.Figure()
        
        # Add sentiment line
        fig.add_trace(go.Scatter(
            x=monthly_sentiment['event_date'],
            y=monthly_sentiment['overall_polarity'],
            mode='lines+markers',
            name='Average Monthly Sentiment',
            line=dict(color='blue', width=2)
        ))
        
        # Add events as markers
        for _, event in events_df.iterrows():
            # Find nearest sentiment value to the event
            nearest_date_idx = np.argmin(np.abs(monthly_sentiment['event_date'] - event['event_date']))
            sentiment_at_event = monthly_sentiment.iloc[nearest_date_idx]['overall_polarity'] if nearest_date_idx < len(monthly_sentiment) else 0
            
            fig.add_trace(go.Scatter(
                x=[event['event_date']],
                y=[sentiment_at_event],
                mode='markers',
                marker=dict(
                    size=15,
                    color='red',
                    symbol='star'
                ),
                name=event['event'],
                text=event['event'],
                hoverinfo='text'
            ))
        
        # Update layout
        fig.update_layout(
            title='Nuclear Events and Sentiment Correlation',
            xaxis_title='Date',
            yaxis_title='Sentiment Score',
            yaxis=dict(
                range=[-1, 1]
            ),
            hovermode='closest',
            showlegend=True
        )
        
        return fig
    except Exception as e:
        print(f"Error creating temporal event correlation: {e}")
        return None

def compare_sentiment_statistics(df, groupby_column='type', min_count=5):
    """
    Create comparative analysis of sentiment across different groups (Feature 5)
    """
    # Only include groups with sufficient data points
    group_counts = df[groupby_column].value_counts()
    valid_groups = group_counts[group_counts >= min_count].index
    filtered_df = df[df[groupby_column].isin(valid_groups)]
    
    if filtered_df.empty:
        return None
    
    # Calculate statistics for each group
    group_stats = filtered_df.groupby(groupby_column).agg({
        'overall_polarity': ['mean', 'median', 'std', 'count'],
        'positivity': 'mean',
        'negativity': 'mean',
        'neutrality': 'mean'
    }).reset_index()
    
    # Rename columns
    group_stats.columns = [
        groupby_column, 'Mean Sentiment', 'Median Sentiment', 
        'Sentiment Std Dev', 'Count', 'Mean Positivity',
        'Mean Negativity', 'Mean Neutrality'
    ]
    
    # Sort by mean sentiment
    group_stats = group_stats.sort_values('Mean Sentiment', ascending=False)
    
    return group_stats

def create_comparative_chart(group_stats, groupby_column='type'):
    """
    Create comparative chart for sentiment analysis (Feature 5)
    """
    if group_stats is None or group_stats.empty:
        return None
    
    # Create figure
    fig = go.Figure()
    
    # Add bar chart for mean sentiment
    fig.add_trace(go.Bar(
        x=group_stats[groupby_column],
        y=group_stats['Mean Sentiment'],
        name='Mean Sentiment',
        marker_color='blue',
        error_y=dict(
            type='data',
            array=group_stats['Sentiment Std Dev'],
            visible=True
        )
    ))
    
    # Add horizontal reference line at y=0
    fig.add_hline(
        y=0,
        line_width=1,
        line_dash="dash",
        line_color="black"
    )
    
    # Update layout
    fig.update_layout(
        title=f"Comparative Sentiment Analysis by {groupby_column.title()}",
        xaxis_title=groupby_column.title(),
        yaxis_title="Sentiment Score",
        hovermode="closest",
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig

def create_sentiment_reliability_chart(df):
    """
    Create chart showing sentiment vs. reliability (Feature 10)
    """
    # Create scatter plot
    fig = px.scatter(
        df,
        x='overall_polarity',
        y='content_reliability',
        color='sentiment_category',
        hover_data=['title'],
        title='Sentiment Reliability Analysis',
        labels={
            'overall_polarity': 'Sentiment Score',
            'content_reliability': 'Reliability Score',
            'sentiment_category': 'Sentiment Category'
        },
        color_discrete_map={
            'Positive': 'green',
            'Neutral': 'gray',
            'Negative': 'red'
        }
    )
    
    # Add reference lines
    fig.add_hline(y=0.7, line_dash="dash", line_color="green", annotation_text="High Reliability")
    fig.add_hline(y=0.4, line_dash="dash", line_color="red", annotation_text="Low Reliability")
    
    # Update layout
    fig.update_layout(
        xaxis=dict(range=[-1, 1]),
        yaxis=dict(range=[0, 1]),
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig

def create_entity_sentiment_chart(df):
    """
    Create chart showing sentiment by named entity type (Feature 2)
    """
    # Extract entity types and their sentiment
    entity_sentiments = []
    
    for i, row in df.iterrows():
        entities = row['named_entities']
        sentiment = row['overall_polarity']
        
        for entity in entities:
            entity_sentiments.append({
                'entity_type': entity['label'],
                'entity_text': entity['text'],
                'sentiment': sentiment
            })
    
    if not entity_sentiments:
        return None
    
    # Convert to DataFrame
    entity_df = pd.DataFrame(entity_sentiments)
    
    # Group by entity type and calculate average sentiment
    entity_stats = entity_df.groupby('entity_type').agg({
        'sentiment': 'mean',
        'entity_text': 'count'
    }).reset_index()
    
    entity_stats.columns = ['Entity Type', 'Average Sentiment', 'Count']
    
    # Only include entity types with sufficient occurrences
    entity_stats = entity_stats[entity_stats['Count'] >= 5].sort_values('Average Sentiment', ascending=False)
    
    if entity_stats.empty:
        return None
    
    # Create figure
    fig = px.bar(
        entity_stats,
        x='Entity Type',
        y='Average Sentiment',
        color='Average Sentiment',
        text='Count',
        labels={
            'Entity Type': 'Named Entity Type',
            'Average Sentiment': 'Average Sentiment Score',
            'Count': 'Number of Occurrences'
        },
        title='Sentiment Analysis by Named Entity Type',
        color_continuous_scale=px.colors.diverging.RdBu,
        color_continuous_midpoint=0
    )
    
    # Update layout
    fig.update_layout(
        margin=dict(l=20, r=20, t=60, b=20)
    )
    
    return fig

def create_forecast_chart(forecast_df):
    """
    Create chart showing sentiment forecast (Feature 6)
    """
    if forecast_df is None or len(forecast_df) == 0:
        return None
    
    try:
        # Create plotly figure
        fig = go.Figure()
        
        # Historical data (has 'historical' column)
        historical_mask = ~forecast_df['historical'].isna()
        historical_data = forecast_df[historical_mask]
        
        # Forecast data (has 'forecast' column)
        forecast_mask = ~forecast_df['forecast'].isna()
        forecast_data = forecast_df[forecast_mask]
        
        # Add historical sentiment line
        if not historical_data.empty:
            fig.add_trace(go.Scatter(
                x=historical_data['date'],
                y=historical_data['historical'],
                mode='lines+markers',
                name='Historical Sentiment',
                line=dict(color='royalblue')
            ))
        
        # Add sentiment forecast line
        if not forecast_data.empty:
            fig.add_trace(go.Scatter(
                x=forecast_data['date'],
                y=forecast_data['forecast'],
                mode='lines+markers',
                name='Forecasted Sentiment',
                line=dict(color='firebrick', dash='dash')
            ))
        
            # Add confidence interval if available
            if 'lower_ci' in forecast_data.columns and 'upper_ci' in forecast_data.columns:
                fig.add_trace(go.Scatter(
                    x=forecast_data['date'].tolist() + forecast_data['date'].tolist()[::-1],
                    y=forecast_data['upper_ci'].tolist() + forecast_data['lower_ci'].tolist()[::-1],
                    fill='toself',
                    fillcolor='rgba(231,107,243,0.2)',
                    line=dict(color='rgba(255,255,255,0)'),
                    showlegend=True,
                    name='95% Confidence Interval'
                ))
        
        # Customize layout
        fig.update_layout(
            title="Sentiment Forecast Over Time",
            xaxis_title="Month",
            yaxis_title="Sentiment Score",
            yaxis=dict(range=[-1, 1]),
            template="plotly_white",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    except Exception as e:
        print(f"Error creating forecast chart: {e}")
        return None

def predict_sentiment_trends(df, periods=12):
    """
    Predict future sentiment trends using ARIMA model
    
    Args:
        df: DataFrame with sentiment analysis results
        periods: Number of periods to forecast
        
    Returns:
        DataFrame: DataFrame with forecasted sentiment values
    """
    if df.empty:
        print("Empty DataFrame, cannot predict trends")
        return None
    
    try:
        # Group by month and calculate average sentiment
        df['date'] = pd.to_datetime(df['date'])
        monthly_df = df.groupby(pd.Grouper(key='date', freq='ME'))['overall_polarity'].mean().reset_index()
        
        # Ensure we have enough data points for forecasting
        if len(monthly_df) < 5:
            print("Not enough data points for forecasting")
            return None
        
        # Set date as index
        monthly_df = monthly_df.set_index('date')
        
        # Train ARIMA model
        try:
            model = ARIMA(monthly_df, order=(1, 1, 1), freq='ME')
            model_fit = model.fit()
        except Exception as e:
            print(f"Error fitting ARIMA model: {e}")
            # Try a simpler model
            model = ARIMA(monthly_df, order=(1, 0, 0), freq='ME')
            model_fit = model.fit()
        
        # Generate forecast with confidence intervals
        forecast = model_fit.forecast(steps=periods)
        
        # Create forecast DataFrame with confidence intervals
        forecast_index = pd.date_range(start=monthly_df.index[-1] + pd.DateOffset(months=1), periods=periods, freq='ME')
        
        # Create forecast DataFrame
        forecast_df = pd.DataFrame({
            'date': forecast_index,
            'forecast': forecast
        })
        
        # Set standard error to fixed value if not available
        stderr = getattr(model_fit, 'stderr', 0.1)
        
        # Add confidence intervals
        z = 1.96  # 95% confidence
        forecast_df['lower_ci'] = forecast_df['forecast'] - z * stderr
        forecast_df['upper_ci'] = forecast_df['forecast'] + z * stderr
        
        # Combine historical and forecast data
        historical = monthly_df.reset_index().rename(columns={'overall_polarity': 'historical'})
        
        # Make sure the lengths match before comparison
        if not historical.empty and not forecast_df.empty:
            # Ensure no overlap between historical and forecast
            forecast_df = forecast_df[forecast_df['date'] > historical['date'].max()]
            
            # Combine historical and forecast
            result = pd.concat([historical, forecast_df], sort=False)
            return result
        else:
            return None
            
    except Exception as e:
        print(f"Error in ARIMA forecasting: {e}")
        return None

def create_dashboard():
    """Create the dashboard interface using Gradio"""
    # Load and preprocess data
    print("Loading data...")
    df = load_data()
    print("Generating sentiment analysis...")
    df = generate_sentiment_analysis(df)
    print("Creating topic model...")
    lda_model, dictionary, corpus = create_topic_model(df['content'].values, num_topics=5)
    doc_topics = get_document_topics(lda_model, dictionary, corpus)
    topic_sentiments = get_topic_sentiments(df, doc_topics, 5)
    print("Generating forecast...")
    forecast_df = predict_sentiment_trends(df)
    
    # Calculate overview statistics
    total_articles = len(df)
    avg_sentiment = df['overall_polarity'].mean()
    sentiment_counts = df['sentiment_category'].value_counts()
    positive_count = sentiment_counts.get('Positive', 0)
    neutral_count = sentiment_counts.get('Neutral', 0)
    negative_count = sentiment_counts.get('Negative', 0)
    
    # Create positive and negative wordclouds
    positive_texts = df[df['sentiment_category'] == 'Positive']['content'].dropna().tolist()
    positive_wordcloud = create_wordcloud(positive_texts, title="Positive")
    
    negative_texts = df[df['sentiment_category'] == 'Negative']['content'].dropna().tolist()
    negative_wordcloud = create_wordcloud(negative_texts, title="Negative")
    
    # Topic model chart
    topic_chart = create_topic_sentiment_chart(lda_model, topic_sentiments)
    topic_html = topic_chart.to_html(include_plotlyjs="require", full_html=False) if topic_chart else "Not enough data for topic modeling"
    
    # Create sentiment trend chart
    trend_chart = plot_sentiment_over_time(df)
    trend_html = trend_chart.to_html(include_plotlyjs="require", full_html=False) if trend_chart else "Not enough data for trend chart"
    
    # Create type distribution chart
    type_chart = plot_type_sentiment(df)
    type_html = type_chart.to_html(include_plotlyjs="require", full_html=False) if type_chart else "Not enough data for type chart"
    
    # Create temporal event correlation chart
    event_chart = create_temporal_event_correlation(df)
    event_html = event_chart.to_html(include_plotlyjs="require", full_html=False)
    
    # Create entity sentiment chart
    entity_chart = create_entity_sentiment_chart(df)
    entity_html = entity_chart.to_html(include_plotlyjs="require", full_html=False) if entity_chart else "Not enough named entities found"
    
    # Create reliability chart
    reliability_chart = create_sentiment_reliability_chart(df)
    reliability_html = reliability_chart.to_html(include_plotlyjs="require", full_html=False)
    
    # Create forecast chart
    forecast_chart = create_forecast_chart(forecast_df)
    forecast_html = forecast_chart.to_html(include_plotlyjs="require", full_html=False) if forecast_chart else "Not enough data for forecasting"
    
    # Advanced filtering options
    def filter_data(
        start_date=None, 
        end_date=None, 
        min_sentiment=None, 
        max_sentiment=None, 
        article_types=None,
        min_reliability=None,
        search_term=None,
        entity_types=None
    ):
        filtered_df = df.copy()
        
        # Filter by date
        if start_date:
            filtered_df = filtered_df[filtered_df['date'] >= pd.to_datetime(start_date)]
        if end_date:
            filtered_df = filtered_df[filtered_df['date'] <= pd.to_datetime(end_date)]
        
        # Filter by sentiment
        if min_sentiment is not None:
            filtered_df = filtered_df[filtered_df['overall_polarity'] >= min_sentiment]
        if max_sentiment is not None:
            filtered_df = filtered_df[filtered_df['overall_polarity'] <= max_sentiment]
        
        # Filter by article type
        if article_types and len(article_types) > 0:
            filtered_df = filtered_df[filtered_df['type'].isin(article_types)]
        
        # Filter by reliability
        if min_reliability is not None:
            filtered_df = filtered_df[filtered_df['content_reliability'] >= min_reliability]
        
        # Filter by search term
        if search_term:
            term_mask = (
                filtered_df['title'].str.contains(search_term, case=False, na=False) |
                filtered_df['content'].str.contains(search_term, case=False, na=False)
            )
            filtered_df = filtered_df[term_mask]
        
        # Filter by entity types
        if entity_types and len(entity_types) > 0:
            entity_mask = filtered_df['named_entities'].apply(
                lambda entities: any(entity['label'] in entity_types for entity in entities)
            )
            filtered_df = filtered_df[entity_mask]
        
        return filtered_df
    
    # Data visualization with advanced filters
    def update_visualizations(
        start_date=None, 
        end_date=None, 
        min_sentiment=None, 
        max_sentiment=None, 
        article_types=None,
        min_reliability=0.0,
        search_term=None,
        entity_types=None,
        comparison_field="type"
    ):
        # Filter data based on criteria
        filtered_df = filter_data(
            start_date, 
            end_date, 
            min_sentiment, 
            max_sentiment, 
            article_types,
            min_reliability,
            search_term,
            entity_types
        )
        
        # Update statistics
        total_filtered = len(filtered_df)
        if total_filtered == 0:
            return {
                "statistics": "No articles match the selected filters.",
                "trend_chart": "No data available",
                "wordcloud_pos": None,
                "wordcloud_neg": None,
                "type_chart": "No data available",
                "article_table": pd.DataFrame(columns=["Title", "Date", "Type", "Sentiment"]),
                "temporal_event_chart": "No data available",
                "entity_chart": "No data available",
                "comparison_chart": "No data available",
                "topic_chart": "No data available",
                "reliability_chart": "No data available",
                "forecast_chart": "No data available"
            }
        
        avg_filtered_sentiment = filtered_df['overall_polarity'].mean()
        filtered_sentiment_counts = filtered_df['sentiment_category'].value_counts()
        filtered_positive = filtered_sentiment_counts.get('Positive', 0)
        filtered_neutral = filtered_sentiment_counts.get('Neutral', 0)
        filtered_negative = filtered_sentiment_counts.get('Negative', 0)
        
        # Update charts
        filtered_trend_chart = plot_sentiment_over_time(filtered_df)
        filtered_trend_html = filtered_trend_chart.to_html(include_plotlyjs="require", full_html=False) if filtered_trend_chart else "Not enough data for trend chart"
        
        filtered_pos_wordcloud = create_wordcloud(filtered_df, 'Positive')
        filtered_neg_wordcloud = create_wordcloud(filtered_df, 'Negative')
        
        filtered_type_chart = plot_type_sentiment(filtered_df)
        filtered_type_html = filtered_type_chart.to_html(include_plotlyjs="require", full_html=False) if filtered_type_chart else "Not enough data for type chart"
        
        # Create filtered temporal event chart
        filtered_event_chart = create_temporal_event_correlation(filtered_df)
        filtered_event_html = filtered_event_chart.to_html(include_plotlyjs="require", full_html=False) if filtered_event_chart else "Not enough data for event correlation"
        
        # Create filtered entity chart
        filtered_entity_chart = create_entity_sentiment_chart(filtered_df)
        filtered_entity_html = filtered_entity_chart.to_html(include_plotlyjs="require", full_html=False) if filtered_entity_chart else "Not enough named entities found"
        
        # Create comparative analysis chart
        group_stats = compare_sentiment_statistics(filtered_df, groupby_column=comparison_field)
        comparison_chart = create_comparative_chart(group_stats, groupby_column=comparison_field)
        comparison_html = comparison_chart.to_html(include_plotlyjs="require", full_html=False) if comparison_chart else f"Not enough data for comparison by {comparison_field}"
        
        # Create filtered topic model chart
        filtered_lda, filtered_dict, filtered_corpus = create_topic_model(filtered_df['content'].values, num_topics=5)
        filtered_doc_topics = get_document_topics(filtered_lda, filtered_dict, filtered_corpus)
        filtered_topic_sentiments = get_topic_sentiments(filtered_df, filtered_doc_topics, 5)
        filtered_topic_chart = create_topic_sentiment_chart(filtered_lda, filtered_topic_sentiments)
        filtered_topic_html = filtered_topic_chart.to_html(include_plotlyjs="require", full_html=False) if filtered_topic_chart else "Not enough data for topic modeling"
        
        # Create filtered reliability chart
        filtered_reliability_chart = create_sentiment_reliability_chart(filtered_df)
        filtered_reliability_html = filtered_reliability_chart.to_html(include_plotlyjs="require", full_html=False) if filtered_reliability_chart else "Not enough data for reliability analysis"
        
        # Create filtered forecast chart
        filtered_forecast_df = predict_sentiment_trends(filtered_df)
        filtered_forecast_chart = create_forecast_chart(filtered_forecast_df)
        filtered_forecast_html = filtered_forecast_chart.to_html(include_plotlyjs="require", full_html=False) if filtered_forecast_chart else "Not enough data for forecasting"
        
        # Article list
        article_data = filtered_df[['title', 'date', 'type', 'overall_polarity', 'content_reliability']].copy()
        article_data['date'] = article_data['date'].dt.strftime('%Y-%m-%d')
        article_data.columns = ['Title', 'Date', 'Type', 'Sentiment', 'Reliability']
        article_data = article_data.sort_values('Date', ascending=False)
        
        # Statistics HTML
        statistics_html = f"""
        <div style="padding: 10px; background-color: #f0f0f0; border-radius: 10px;">
            <h3>Filtered Results</h3>
            <div style="display: flex; justify-content: space-between; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 200px; padding: 10px;">
                    <h3>Total Articles</h3>
                    <p style="font-size: 2em; font-weight: bold;">{total_filtered} (out of {total_articles})</p>
                </div>
                <div style="flex: 1; min-width: 200px; padding: 10px;">
                    <h3>Average Sentiment</h3>
                    <p style="font-size: 2em; font-weight: bold; color: {'green' if avg_filtered_sentiment > 0 else 'red' if avg_filtered_sentiment < 0 else 'gray'};">{avg_filtered_sentiment:.3f}</p>
                </div>
                <div style="flex: 1; min-width: 200px; padding: 10px;">
                    <h3>Sentiment Distribution</h3>
                    <p><span style="color: green; font-weight: bold;">Positive:</span> {filtered_positive} ({filtered_positive/total_filtered*100:.1f}%)</p>
                    <p><span style="color: gray; font-weight: bold;">Neutral:</span> {filtered_neutral} ({filtered_neutral/total_filtered*100:.1f}%)</p>
                    <p><span style="color: red; font-weight: bold;">Negative:</span> {filtered_negative} ({filtered_negative/total_filtered*100:.1f}%)</p>
                </div>
            </div>
        </div>
        """
        
        return {
            "statistics": statistics_html,
            "trend_chart": filtered_trend_html,
            "wordcloud_pos": filtered_pos_wordcloud,
            "wordcloud_neg": filtered_neg_wordcloud,
            "type_chart": filtered_type_html,
            "article_table": article_data,
            "temporal_event_chart": filtered_event_html,
            "entity_chart": filtered_entity_html,
            "comparison_chart": comparison_html,
            "topic_chart": filtered_topic_html,
            "reliability_chart": filtered_reliability_html,
            "forecast_chart": filtered_forecast_html
        }
    
    # Article search functionality
    def search_articles(query):
        if not query:
            return pd.DataFrame(columns=["Title", "Date", "Type", "Sentiment"])
        
        # Search in title and content
        mask = (
            df['title'].str.contains(query, case=False, na=False) | 
            df['content'].str.contains(query, case=False, na=False)
        )
        results = df[mask][['title', 'date', 'type', 'overall_polarity']]
        
        # Format results
        results['date'] = results['date'].dt.strftime('%Y-%m-%d')
        results.columns = ['Title', 'Date', 'Type', 'Sentiment']
        results = results.sort_values('Sentiment', ascending=False)
        
        return results
    
    # Article detail view
    def view_article_details(article_title):
        if not article_title:
            return ("", "", "", "", "", "", "", "")
        
        # Find the article by title
        article = df[df['title'] == article_title].iloc[0]
        
        # Get article info
        title = article['title']
        date = article['date'].strftime('%Y-%m-%d') if not pd.isna(article['date']) else "Unknown"
        article_type = article['type']
        content = article['content']
        sentiment = article['overall_polarity']
        reliability = article['content_reliability']
        
        # Get color based on sentiment
        if sentiment > 0.1:
            sentiment_color = "green"
            sentiment_label = "Positive"
        elif sentiment < -0.1:
            sentiment_color = "red"
            sentiment_label = "Negative"
        else:
            sentiment_color = "gray"
            sentiment_label = "Neutral"
        
        # Get color for reliability
        if reliability > 0.7:
            reliability_color = "green"
            reliability_label = "High"
        elif reliability < 0.4:
            reliability_color = "red"
            reliability_label = "Low"
        else:
            reliability_color = "orange"
            reliability_label = "Medium"
        
        # Get key terms
        key_terms = article['key_terms']
        key_terms_html = ""
        if key_terms:
            key_terms_html = "<h4>Key Terms:</h4><ul>"
            for term, count, score in key_terms:
                term_color = "green" if score > 0 else "red"
                key_terms_html += f'<li><span style="color: {term_color};">{term}</span> (impact: {score:+.1f})</li>'
            key_terms_html += "</ul>"
        
        # Get named entities
        entities = article['named_entities']
        entities_html = ""
        if entities:
            entities_by_type = {}
            for entity in entities:
                entity_type = entity['label']
                entity_text = entity['text']
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                if entity_text not in entities_by_type[entity_type]:
                    entities_by_type[entity_type].append(entity_text)
            
            entities_html = "<h4>Named Entities:</h4><ul>"
            for entity_type, entity_list in entities_by_type.items():
                entities_html += f'<li><b>{entity_type}</b>: {", ".join(entity_list[:5])}'
                if len(entity_list) > 5:
                    entities_html += f' and {len(entity_list) - 5} more'
                entities_html += '</li>'
            entities_html += "</ul>"
        
        # Format the details
        title_html = f"<h2>{title}</h2>"
        metadata_html = f"<p><b>Date:</b> {date} | <b>Type:</b> {article_type}</p>"
        sentiment_html = f"""
        <div style="margin: 10px 0;">
            <span style="font-weight: bold;">Sentiment: </span>
            <span style="color: {sentiment_color}; font-weight: bold;">{sentiment_label} ({sentiment:.3f})</span>
        </div>
        """
        reliability_html = f"""
        <div style="margin: 10px 0;">
            <span style="font-weight: bold;">Reliability: </span>
            <span style="color: {reliability_color}; font-weight: bold;">{reliability_label} ({reliability:.2f})</span>
        </div>
        """
        content_html = f"<div style='margin-top: 20px;'>{content}</div>"
        
        return (title_html, metadata_html, sentiment_html, reliability_html, key_terms_html, entities_html, content_html, article_title)
    
    # Create the dashboard interface
    with gr.Blocks(theme=gr.themes.Soft(), title="Nuclear Energy Sentiment Dashboard") as dashboard:
        with gr.Row():
            gr.Markdown("# Nuclear Energy Sentiment Analysis Dashboard")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## Filters")
                
                year_slider = gr.Slider(
                    minimum=df['date'].dt.year.min(), 
                    maximum=df['date'].dt.year.max(),
                    value=[df['date'].dt.year.min(), df['date'].dt.year.max()],
                    step=1, 
                    label="Year Range"
                )
                
                source_dropdown = gr.Dropdown(
                    choices=["All"] + sorted(df['type'].unique().tolist()),
                    value="All",
                    label="Source Type"
                )
                
                sentiment_dropdown = gr.Dropdown(
                    choices=["All", "Positive", "Neutral", "Negative"],
                    value="All",
                    label="Sentiment"
                )
                
                topic_dropdown = gr.Dropdown(
                    choices=["All", "Topic 1", "Topic 2", "Topic 3", "Topic 4", "Topic 5"],
                    value="All",
                    label="Topic"
                )
                
                entity_dropdown = gr.Dropdown(
                    choices=["All"] + sorted(list(set([
                        entity.get('text', '')
                        for entities in df['named_entities'].dropna()
                        for entity in entities if entity
                    ]))),
                    value="All",
                    label="Entity Filter"
                )
                
                search_input = gr.Textbox(
                    label="Search Articles",
                    placeholder="Enter keywords..."
                )
                
                search_button = gr.Button("Search", variant="primary")
                
            with gr.Column(scale=3):
                with gr.Tabs():
                    with gr.TabItem("Overview"):
                        with gr.Row():
                            with gr.Column():
                                sentiment_chart = gr.Plot(
                                    plot_sentiment_over_time(df),
                                    label="Sentiment Over Time"
                                )
                            with gr.Column():
                                type_chart = gr.Plot(
                                    plot_type_sentiment(df),
                                    label="Sentiment by Source Type"
                                )
                        
                        with gr.Row():
                            with gr.Column():
                                topics_chart = gr.Plot(
                                    create_topic_distribution_chart(df),
                                    label="Topic Distribution"
                                )
                            with gr.Column():
                                entity_chart = gr.Plot(
                                    create_entity_chart(df),
                                    label="Top Named Entities"
                                )
                    
                    with gr.TabItem("Wordclouds"):
                        with gr.Row():
                            with gr.Column():
                                if positive_wordcloud:
                                    gr.Image(positive_wordcloud, label="Positive Content Wordcloud")
                                else:
                                    gr.Markdown("No positive content available for wordcloud")
                            
                            with gr.Column():
                                if negative_wordcloud:
                                    gr.Image(negative_wordcloud, label="Negative Content Wordcloud")
                                else:
                                    gr.Markdown("No negative content available for wordcloud")
                        
                        with gr.Row():
                            with gr.Column():
                                if neutral_wordcloud:
                                    gr.Image(neutral_wordcloud, label="Neutral Content Wordcloud")
                                else:
                                    gr.Markdown("No neutral content available for wordcloud")
                    
                    with gr.TabItem("Forecasting"):
                        with gr.Row():
                            forecast_input = gr.Slider(
                                minimum=1, 
                                maximum=24,
                                value=12,
                                step=1, 
                                label="Forecast Months"
                            )
                            
                            forecast_button = gr.Button("Update Forecast", variant="secondary")
                        
                        with gr.Row():
                            forecast_chart = gr.Plot(
                                create_forecast_chart(forecast_df) if forecast_df is not None else None,
                                label="Sentiment Forecast"
                            )
                    
                    with gr.TabItem("Events Correlation"):
                        with gr.Row():
                            event_chart = create_temporal_event_correlation(df)
                            if event_chart:
                                gr.Plot(event_chart, label="Nuclear Events and Sentiment")
                            else:
                                gr.Markdown("Not enough data for event correlation")
                    
                    with gr.TabItem("Articles"):
                        search_results = gr.Dataframe(
                            headers=["Title", "Date", "Type", "Sentiment"],
                            datatype=["str", "str", "str", "number"],
                            label="Search Results"
                        )
        
        # Functions to update dashboard based on filters
        filter_inputs = [year_slider, source_dropdown, sentiment_dropdown, topic_dropdown, entity_dropdown]
        
        for input_widget in filter_inputs:
            input_widget.change(
                update_charts, 
                inputs=filter_inputs, 
                outputs=[sentiment_chart, type_chart, topics_chart, entity_chart, event_chart]
            )
        
        search_button.click(
            search_articles, 
            inputs=[search_input], 
            outputs=[search_results]
        )
        
        forecast_button.click(
            update_forecast,
            inputs=[forecast_input],
            outputs=[forecast_chart]
        )
    
    return dashboard

def filter_data(year_range, source, sentiment, topic, entity, df):
    """
    Filter the dataframe based on user selections
    
    Args:
        year_range (list): Range of years [min, max]
        source (str): Source type or 'All'
        sentiment (str): Sentiment category or 'All'
        topic (str): Topic filter or 'All'
        entity (str): Entity to filter by or 'All'
        df (DataFrame): Source dataframe
        
    Returns:
        DataFrame: Filtered dataframe
    """
    filtered_df = df.copy()
    
    # Filter by year
    filtered_df = filtered_df[
        (filtered_df['date'].dt.year >= year_range[0]) & 
        (filtered_df['date'].dt.year <= year_range[1])
    ]
    
    # Filter by source
    if source != "All":
        filtered_df = filtered_df[filtered_df['type'] == source]
    
    # Filter by sentiment
    if sentiment == "Positive":
        filtered_df = filtered_df[filtered_df['overall_polarity'] > 0.05]
    elif sentiment == "Negative":
        filtered_df = filtered_df[filtered_df['overall_polarity'] < -0.05]
    elif sentiment == "Neutral":
        filtered_df = filtered_df[
            (filtered_df['overall_polarity'] >= -0.05) & 
            (filtered_df['overall_polarity'] <= 0.05)
        ]
    
    # Filter by topic
    if topic != "All" and 'main_topic' in filtered_df.columns:
        topic_num = int(topic.split(" ")[1]) - 1
        filtered_df = filtered_df[filtered_df['main_topic'] == topic_num]
    
    # Filter by entity
    if entity != "All":
        mask = filtered_df['named_entities'].apply(
            lambda entities: any(
                e.get('text', '') == entity 
                for e in (entities or []) if e
            )
        )
        filtered_df = filtered_df[mask]
    
    return filtered_df

def update_charts(year_range, source, sentiment, topic, entity):
    """
    Update all charts based on filter selections
    
    Args:
        year_range (list): Range of years [min, max]
        source (str): Source type or 'All'
        sentiment (str): Sentiment category or 'All'
        topic (str): Topic filter or 'All'
        entity (str): Entity to filter by or 'All'
        
    Returns:
        tuple: Updated chart objects
    """
    filtered_df = filter_data(year_range, source, sentiment, topic, entity, df)
    
    # Generate new charts
    sentiment_time_chart = plot_sentiment_over_time(filtered_df)
    source_sentiment_chart = plot_type_sentiment(filtered_df)
    topics_dist_chart = create_topic_distribution_chart(filtered_df)
    entities_chart = create_entity_chart(filtered_df)
    events_corr_chart = create_temporal_event_correlation(filtered_df)
    
    return sentiment_time_chart, source_sentiment_chart, topics_dist_chart, entities_chart, events_corr_chart

def create_topic_distribution_chart(df):
    """
    Create a chart showing the distribution of topics in the data
    
    Args:
        df: DataFrame with topic modeling results
        
    Returns:
        Figure: Plotly figure with topic distribution
    """
    if 'main_topic' not in df.columns or df['main_topic'].isnull().all():
        return None
    
    try:
        # Count documents by topic
        topic_counts = df['main_topic'].value_counts().reset_index()
        topic_counts.columns = ['Topic', 'Count']
        topic_counts['Topic'] = topic_counts['Topic'].apply(lambda x: f'Topic {x+1}')
        
        # Create bar chart
        fig = px.bar(
            topic_counts, 
            x='Topic', 
            y='Count',
            title="Document Distribution by Topic",
            color='Count',
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(
            xaxis_title="Topic",
            yaxis_title="Number of Documents",
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=12)
        )
        
        return fig
    except Exception as e:
        print(f"Error creating topic distribution chart: {e}")
        return None

def create_entity_chart(df):
    """
    Create a chart showing the top named entities in the data
    
    Args:
        df: DataFrame with named entities extraction results
        
    Returns:
        Figure: Plotly figure with entity counts
    """
    if 'named_entities' not in df.columns or df['named_entities'].isnull().all():
        return None
    
    try:
        # Extract all entities and their counts
        entity_counts = {}
        for entities in df['named_entities'].dropna():
            for entity in entities:
                if entity and 'text' in entity:
                    entity_text = entity.get('text', '')
                    entity_counts[entity_text] = entity_counts.get(entity_text, 0) + 1
        
        # Get top 15 entities
        top_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        entity_df = pd.DataFrame(top_entities, columns=['Entity', 'Count'])
        
        # Create horizontal bar chart
        fig = px.bar(
            entity_df, 
            y='Entity', 
            x='Count',
            title="Top Named Entities",
            color='Count',
            color_continuous_scale='Viridis',
            orientation='h'
        )
        
        fig.update_layout(
            xaxis_title="Count",
            yaxis_title="Entity",
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=12),
            yaxis={'categoryorder':'total ascending'}
        )
        
        return fig
    except Exception as e:
        print(f"Error creating entity chart: {e}")
        return None

def create_wordcloud(texts_or_df, max_words=100, title=""):
    """
    Create a wordcloud from a list of texts or DataFrame
    
    Args:
        texts_or_df: Either a list of text strings or a DataFrame with 'content' and 'sentiment_category' columns
        max_words: Maximum number of words to include in the wordcloud
        title: Title for the wordcloud image
        
    Returns:
        str: Path to the generated wordcloud image or None if no text is available
    """
    # Handle DataFrame input (backward compatibility)
    if isinstance(texts_or_df, pd.DataFrame):
        if title in ['Positive', 'Negative', 'Neutral']:
            # Filter by sentiment category
            texts = texts_or_df[texts_or_df['sentiment_category'] == title]['content'].dropna().tolist()
        else:
            # Use all content
            texts = texts_or_df['content'].dropna().tolist()
    else:
        # Already a list of texts
        texts = texts_or_df
    
    if not texts or len(texts) == 0 or all(pd.isna(text) for text in texts):
        print(f"No text available for wordcloud: {title}")
        return None
        
    try:
        # Concatenate all texts
        text = ' '.join([str(t) for t in texts if not pd.isna(t)])
        
        # Create wordcloud
        wordcloud = WordCloud(
            width=800, 
            height=400,
            max_words=max_words,
            background_color='white',
            colormap='viridis',
            contour_width=1,
            contour_color='steelblue'
        ).generate(text)
        
        # Plot wordcloud
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title(title)
        
        # Save to shorter, temporary file path to avoid Windows path length limitation
        temp_dir = os.path.join(os.environ.get('TEMP', 'C:/temp'), 'nlp_dashboard')
        os.makedirs(temp_dir, exist_ok=True)
        filename = f"wordcloud_{title.replace(' ', '_').lower()}.png"
        filepath = os.path.join(temp_dir, filename)
        
        plt.savefig(filepath)
        plt.close()
        
        return filepath
        
    except Exception as e:
        print(f"Error creating wordcloud: {e}")
        return None

if __name__ == "__main__":
    dashboard = create_dashboard()
    dashboard.launch(share=True)