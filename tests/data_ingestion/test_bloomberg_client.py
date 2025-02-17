"""
Unit tests for Bloomberg API client.
"""

import pytest
import datetime
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from src.data_ingestion.bloomberg_client import BloombergClient

@pytest.fixture
def mock_session():
    """Create a mock Bloomberg session."""
    session = Mock()
    session.start.return_value = True
    session.openService.return_value = True
    return session

@pytest.fixture
def mock_blpapi():
    """Create a mock blpapi module."""
    blpapi = Mock()
    blpapi.Session = Mock()
    blpapi.SessionOptions = Mock()
    blpapi.AuthOptions = Mock()
    blpapi.CorrelationId = Mock()
    blpapi.Event.RESPONSE = 'RESPONSE'
    return blpapi

@pytest.fixture
def client(mock_blpapi, mock_session):
    """Create a Bloomberg client with mocked dependencies."""
    with patch('src.data_ingestion.bloomberg_client.blpapi', mock_blpapi):
        mock_blpapi.Session.return_value = mock_session
        config = {
            'bloomberg_host': 'localhost',
            'bloomberg_port': 8194,
            'bloomberg_auth': {
                'username': 'test',
                'password': 'test'
            }
        }
        return BloombergClient(config)

def test_connect(client, mock_session):
    """Test connection to Bloomberg API."""
    assert client.connect() is True
    mock_session.start.assert_called_once()
    assert mock_session.openService.call_count == 4

def test_connect_failure(client, mock_session):
    """Test connection failure handling."""
    mock_session.start.return_value = False
    assert client.connect() is False

def test_disconnect(client, mock_session):
    """Test disconnection from Bloomberg API."""
    client.connect()
    client.disconnect()
    mock_session.stop.assert_called_once()

def test_fetch_news_articles(client, mock_session):
    """Test news article fetching."""
    # Mock response message
    mock_msg = Mock()
    mock_msg.correlationIds.return_value = [Mock(value=lambda: "NewsSearch")]
    mock_msg.hasElement.return_value = True
    
    # Mock article data
    mock_article = Mock()
    mock_article.getElementAsString.side_effect = lambda x: {
        "headline": "Test Headline",
        "body": "Test Body",
        "source": "Test Source",
        "uri": "test://uri"
    }[x]
    mock_article.getElementAsDatetime.return_value = datetime.datetime.now()
    mock_article.hasElement.return_value = False
    
    # Mock articles element
    mock_articles = Mock()
    mock_articles.numValues.return_value = 1
    mock_articles.getValueAsElement.return_value = mock_article
    
    # Set up message structure
    mock_msg.getElement.side_effect = lambda x: {
        "totalResults": Mock(getValueAsInteger=lambda: 1),
        "articles": mock_articles
    }[x]
    
    # Mock event
    mock_event = Mock()
    mock_event.eventType.return_value = "RESPONSE"
    mock_event.__iter__ = lambda x: iter([mock_msg])
    
    # Set up session response
    mock_session.nextEvent.return_value = mock_event
    
    # Test article fetching
    articles = client.fetch_news_articles(
        topics=["nuclear energy"],
        start_date=datetime.datetime.now()
    )
    
    assert len(articles) == 1
    assert articles[0]['headline'] == "Test Headline"
    assert articles[0]['body'] == "Test Body"
    assert articles[0]['source'] == "Test Source"

def test_fetch_company_data(client, mock_session):
    """Test company data fetching."""
    # Mock response message
    mock_msg = Mock()
    
    # Mock security data
    mock_security_data = Mock()
    mock_security_data.getElementAsString.return_value = "TEST"
    
    # Mock field data
    mock_field_values = Mock()
    mock_field_values.hasElement.return_value = True
    mock_field_values.getElementAsFloat.return_value = 100.0
    mock_field_values.getElementAsDatetime.return_value = datetime.datetime.now()
    
    # Mock field data container
    mock_field_data = Mock()
    mock_field_data.numValues.return_value = 1
    mock_field_data.getValueAsElement.return_value = mock_field_values
    
    # Set up message structure
    mock_security_data.getElement.return_value = mock_field_data
    mock_msg.getElement.return_value = mock_security_data
    
    # Mock event
    mock_event = Mock()
    mock_event.eventType.return_value = "RESPONSE"
    mock_event.__iter__ = lambda x: iter([mock_msg])
    
    # Set up session response
    mock_session.nextEvent.return_value = mock_event
    
    # Test data fetching
    df = client.fetch_company_data(
        companies=["TEST"],
        fields=["PX_LAST"],
        start_date=datetime.datetime.now()
    )
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty

def test_subscribe_to_market_data(client, mock_session):
    """Test market data subscription."""
    callback = Mock()
    result = client.subscribe_to_market_data(
        securities=["TEST"],
        fields=["PX_LAST"],
        callback=callback
    )
    
    assert result is True
    mock_session.subscribe.assert_called_once()

def test_get_field_info(client, mock_session):
    """Test field info retrieval."""
    # Mock response message
    mock_msg = Mock()
    mock_msg.hasElement.return_value = True
    
    # Mock field data
    mock_field_data = Mock()
    mock_field_data.getElementAsString.side_effect = lambda x: {
        "id": "TEST",
        "mnemonic": "TEST_MNEMONIC",
        "description": "Test Description",
        "documentation": "Test Documentation",
        "datatype": "String"
    }[x]
    
    # Set up message structure
    mock_msg.getElement.return_value = mock_field_data
    
    # Mock event
    mock_event = Mock()
    mock_event.eventType.return_value = "RESPONSE"
    mock_event.__iter__ = lambda x: iter([mock_msg])
    
    # Set up session response
    mock_session.nextEvent.return_value = mock_event
    
    # Test field info retrieval
    field_info = client.get_field_info("TEST")
    
    assert field_info['id'] == "TEST"
    assert field_info['mnemonic'] == "TEST_MNEMONIC"
    assert field_info['description'] == "Test Description"

def test_context_manager(client, mock_session):
    """Test context manager functionality."""
    with client as c:
        assert c.session is mock_session
    
    mock_session.stop.assert_called_once()

def test_fetch_esg_data(client, mock_session):
    """Test ESG data fetching."""
    # Mock response message
    mock_msg = Mock()
    
    # Mock security data
    mock_security_data = Mock()
    mock_security_data.numValues.return_value = 1
    
    # Mock security
    mock_security = Mock()
    mock_security.getElementAsString.return_value = "TEST"
    
    # Mock field data
    mock_field_data = Mock()
    mock_field_data.hasElement.return_value = True
    mock_field_data.getElementAsFloat.return_value = 75.5
    
    # Set up message structure
    mock_security.getElement.return_value = mock_field_data
    mock_security_data.getValueAsElement.return_value = mock_security
    mock_msg.getElement.return_value = mock_security_data
    
    # Mock event
    mock_event = Mock()
    mock_event.eventType.return_value = "RESPONSE"
    mock_event.__iter__ = lambda x: iter([mock_msg])
    
    # Set up session response
    mock_session.nextEvent.return_value = mock_event
    
    # Test ESG data fetching
    df = client.fetch_esg_data(["TEST"])
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "ESG_DISCLOSURE_SCORE" in df.columns

def test_fetch_nuclear_indices(client, mock_session):
    """Test nuclear indices fetching."""
    # Mock response message
    mock_msg = Mock()
    
    # Mock security data
    mock_security_data = Mock()
    mock_security_data.getElementAsString.return_value = "NUCLEAR_INDEX"
    
    # Mock field data
    mock_field_values = Mock()
    mock_field_values.hasElement.return_value = True
    mock_field_values.getElementAsFloat.return_value = 1000.0
    mock_field_values.getElementAsDatetime.return_value = datetime.datetime.now()
    
    # Mock field data container
    mock_field_data = Mock()
    mock_field_data.numValues.return_value = 1
    mock_field_data.getValueAsElement.return_value = mock_field_values
    
    # Set up message structure
    mock_security_data.getElement.return_value = mock_field_data
    mock_msg.getElement.return_value = mock_security_data
    
    # Mock event
    mock_event = Mock()
    mock_event.eventType.return_value = "RESPONSE"
    mock_event.__iter__ = lambda x: iter([mock_msg])
    
    # Set up session response
    mock_session.nextEvent.return_value = mock_event
    
    # Test indices fetching
    df = client.fetch_nuclear_indices()
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "PX_LAST" in df.columns

def test_analyze_sentiment_trends(client, mock_session):
    """Test sentiment trend analysis."""
    # Mock news articles
    mock_articles = [
        {
            'headline': 'Test Headline 1',
            'body': 'Positive test content',
            'date': datetime.datetime.now(),
            'source': 'Test Source',
            'uri': 'test://uri1'
        },
        {
            'headline': 'Test Headline 2',
            'body': 'Negative test content',
            'date': datetime.datetime.now() - datetime.timedelta(days=1),
            'source': 'Test Source',
            'uri': 'test://uri2'
        }
    ]
    
    # Mock sentiment analysis
    with patch.object(client, 'fetch_news_articles', return_value=mock_articles):
        with patch.object(client, '_extract_sentiment', side_effect=[0.8, -0.5]):
            trends, stats = client.analyze_sentiment_trends(
                topics=["nuclear energy"],
                lookback_days=7,
                interval='daily'
            )
    
    assert isinstance(trends, pd.DataFrame)
    assert isinstance(stats, dict)
    assert 'overall_sentiment' in stats
    assert 'total_articles' in stats
    assert stats['total_articles'] == 2

def test_get_company_events(client, mock_session):
    """Test company event fetching."""
    # Mock response message
    mock_msg = Mock()
    
    # Mock calendar data
    mock_calendar_data = Mock()
    mock_calendar_data.numValues.return_value = 1
    
    # Mock calendar event
    mock_event_data = Mock()
    mock_event_data.getElementAsDatetime.return_value = datetime.datetime.now()
    mock_event_data.getElementAsString.side_effect = lambda x: {
        "type": "earnings",
        "description": "Q4 2024 Earnings Release"
    }[x]
    mock_event_data.hasElement.return_value = True
    
    # Mock event details
    mock_details = Mock()
    mock_details.numElements.return_value = 1
    mock_details.getElement.return_value = Mock(
        name=lambda: "time",
        getValueAsString=lambda: "09:00"
    )
    
    # Set up message structure
    mock_event_data.getElement.return_value = mock_details
    mock_calendar_data.getValueAsElement.return_value = mock_event_data
    mock_msg.getElement.return_value = mock_calendar_data
    
    # Mock event
    mock_event = Mock()
    mock_event.eventType.return_value = "RESPONSE"
    mock_event.__iter__ = lambda x: iter([mock_msg])
    
    # Set up session response
    mock_session.nextEvent.return_value = mock_event
    
    # Test event fetching
    events = client.get_company_events("TEST")
    
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0]['type'] == "earnings"
    assert 'details' in events[0]

def test_extract_sentiment(client, mock_session):
    """Test sentiment extraction."""
    # Mock response message
    mock_msg = Mock()
    mock_msg.hasElement.return_value = True
    
    # Mock sentiment data
    mock_sentiment = Mock()
    mock_sentiment.getElementAsFloat.return_value = 0.75
    
    # Set up message structure
    mock_msg.getElement.return_value = mock_sentiment
    
    # Mock event
    mock_event = Mock()
    mock_event.eventType.return_value = "RESPONSE"
    mock_event.__iter__ = lambda x: iter([mock_msg])
    
    # Set up session response
    mock_session.nextEvent.return_value = mock_event
    
    # Test sentiment extraction
    score = client._extract_sentiment("Test positive content")
    
    assert isinstance(score, float)
    assert -1 <= score <= 1
