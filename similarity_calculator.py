import nltk
import logging
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import string
import re

# Configure logging
logger = logging.getLogger(__name__)

# Download necessary NLTK resources
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
except Exception as e:
    logger.warning(f"Error downloading NLTK resources: {str(e)}")

def calculate_similarity(skills, job_description):
    """
    Calculate similarity score between resume skills and job description
    
    Args:
        skills: List of skills extracted from the resume
        job_description: Job description text
        
    Returns:
        Similarity score as a percentage
    """
    try:
        if not skills or not job_description:
            return 0
        
        # Preprocess job description
        processed_job_desc = preprocess_text(job_description)
        
        # Count matches
        match_count = 0
        for skill in skills:
            skill_tokens = preprocess_text(skill)
            
            # Check if skill tokens appear in job description
            if all(token in processed_job_desc for token in skill_tokens):
                match_count += 1
            # Alternative: check if any token appears
            elif any(token in processed_job_desc for token in skill_tokens):
                match_count += 0.5
        
        # Calculate similarity percentage
        if len(skills) > 0:
            similarity = (match_count / len(skills)) * 100
            return round(similarity, 2)
        return 0
    
    except Exception as e:
        logger.error(f"Error calculating similarity: {str(e)}", exc_info=True)
        return 0

def preprocess_text(text):
    """
    Preprocess text for comparison
    
    Args:
        text: Text to preprocess
        
    Returns:
        List of processed tokens
    """
    try:
        # Convert to lowercase
        text = text.lower()
        
        # Remove punctuation
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stopwords
        stop_words = set(stopwords.words('english'))
        tokens = [word for word in tokens if word not in stop_words]
        
        # Lemmatize
        lemmatizer = WordNetLemmatizer()
        tokens = [lemmatizer.lemmatize(word) for word in tokens]
        
        return tokens
    
    except Exception as e:
        logger.error(f"Error preprocessing text: {str(e)}", exc_info=True)
        return []

def extract_keywords_from_job_description(job_description):
    """
    Extract important keywords from job description
    
    Args:
        job_description: Job description text
        
    Returns:
        List of keywords
    """
    try:
        # Preprocess text
        tokens = preprocess_text(job_description)
        
        # Simple approach: count frequency of words
        word_freq = {}
        for token in tokens:
            if token in word_freq:
                word_freq[token] += 1
            else:
                word_freq[token] = 1
        
        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Take top 20 words as keywords
        keywords = [word for word, freq in sorted_words[:20] if len(word) > 2]
        
        return keywords
    
    except Exception as e:
        logger.error(f"Error extracting keywords: {str(e)}", exc_info=True)
        return []
