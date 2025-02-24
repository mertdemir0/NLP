"""Text preprocessing and cleaning utilities."""
import re
import string
import logging
from typing import List, Optional
import spacy
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    logger.info("Successfully downloaded NLTK data")
except Exception as e:
    logger.warning(f"Failed to download NLTK data: {str(e)}. Some functionality may be limited.")

# Load spaCy model
try:
    nlp = spacy.load('en_core_web_lg')
    logger.info("Successfully loaded spaCy model 'en_core_web_lg'")
except OSError:
    logger.warning("Could not load 'en_core_web_lg'. Attempting to load 'en_core_web_sm' as fallback...")
    try:
        nlp = spacy.load('en_core_web_sm')
        logger.info("Successfully loaded fallback spaCy model 'en_core_web_sm'")
    except OSError as e:
        logger.error(f"Failed to load spaCy models: {str(e)}. Named entity recognition will be disabled.")
        nlp = None

class TextCleaner:
    """Class for cleaning and preprocessing text data."""
    
    def __init__(self, 
                 remove_urls: bool = True,
                 remove_numbers: bool = False,
                 remove_punctuation: bool = True,
                 convert_lowercase: bool = True,
                 remove_stopwords: bool = True,
                 lemmatize: bool = True,
                 min_token_length: int = 3,
                 custom_stopwords: Optional[List[str]] = None):
        """Initialize the text cleaner with specified options.
        
        Args:
            remove_urls: Whether to remove URLs from text
            remove_numbers: Whether to remove numbers from text
            remove_punctuation: Whether to remove punctuation
            convert_lowercase: Whether to convert text to lowercase
            remove_stopwords: Whether to remove stopwords
            lemmatize: Whether to lemmatize tokens
            min_token_length: Minimum length for a token to be kept
            custom_stopwords: Additional stopwords to remove
        """
        self.remove_urls = remove_urls
        self.remove_numbers = remove_numbers
        self.remove_punctuation = remove_punctuation
        self.convert_lowercase = convert_lowercase
        self.remove_stopwords = remove_stopwords
        self.lemmatize = lemmatize
        self.min_token_length = min_token_length
        
        # Initialize stopwords
        self.stopwords = set(stopwords.words('english'))
        if custom_stopwords:
            self.stopwords.update(custom_stopwords)
        
        # Initialize lemmatizer
        self.lemmatizer = WordNetLemmatizer()
    
    def clean_text(self, text: str) -> str:
        """Clean text using specified options.
        
        Args:
            text: Input text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove URLs
        if self.remove_urls:
            text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        
        # Convert to lowercase
        if self.convert_lowercase:
            text = text.lower()
        
        # Remove numbers
        if self.remove_numbers:
            text = re.sub(r'\d+', '', text)
        
        # Remove punctuation
        if self.remove_punctuation:
            text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stopwords and short tokens
        if self.remove_stopwords:
            tokens = [token for token in tokens 
                     if token not in self.stopwords 
                     and len(token) >= self.min_token_length]
        
        # Lemmatize
        if self.lemmatize:
            tokens = [self.lemmatizer.lemmatize(token) for token in tokens]
        
        return ' '.join(tokens)
    
    def clean_texts(self, texts: List[str]) -> List[str]:
        """Clean multiple texts.
        
        Args:
            texts: List of texts to clean
            
        Returns:
            List of cleaned texts
        """
        return [self.clean_text(text) for text in texts]
    
    def extract_named_entities(self, text: str) -> List[tuple]:
        """Extract named entities from text using spaCy.
        
        Args:
            text: Input text
            
        Returns:
            List of (entity_text, entity_label) tuples
        """
        if nlp is None:
            logger.error("Named entity recognition is disabled due to spaCy model loading failure.")
            return []
        
        doc = nlp(text)
        return [(ent.text, ent.label_) for ent in doc.ents]
    
    def extract_sentences(self, text: str) -> List[str]:
        """Split text into sentences.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        return sent_tokenize(text)
    
    def get_pos_tags(self, text: str) -> List[tuple]:
        """Get part-of-speech tags for text.
        
        Args:
            text: Input text
            
        Returns:
            List of (token, pos_tag) tuples
        """
        tokens = word_tokenize(text)
        return nltk.pos_tag(tokens)
    
    @staticmethod
    def remove_special_characters(text: str) -> str:
        """Remove special characters from text.
        
        Args:
            text: Input text
            
        Returns:
            Text with special characters removed
        """
        return re.sub(r'[^a-zA-Z0-9\s]', '', text)