import nltk
import logging
from nltk.tokenize import RegexpTokenizer
from nltk.stem import PorterStemmer
import string
import re
import os

# Configure logging
logger = logging.getLogger(__name__)

# Set NLTK data path
nltk_data_path = os.path.join(os.getcwd(), 'nltk_data')
os.makedirs(nltk_data_path, exist_ok=True)
nltk.data.path.append(nltk_data_path)

# Download necessary NLTK resources
try:
    nltk.download('punkt', download_dir=nltk_data_path, quiet=True)
    nltk.download('stopwords', download_dir=nltk_data_path, quiet=True)
    nltk.download('wordnet', download_dir=nltk_data_path, quiet=True)
    
    # Import resources after downloading
    from nltk.corpus import stopwords
except Exception as e:
    logger.warning(f"Error downloading NLTK resources: {str(e)}")
    # Define a basic set of stopwords if download fails
    BASIC_STOPWORDS = set([
        'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 
        'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 
        'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 
        'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this',
        'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 
        'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 
        'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 
        'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
        'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 
        'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 
        'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 
        'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 
        'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 
        't', 'can', 'will', 'just', 'don', 'should', 'now'
    ])

# Create tokenizer that excludes punctuation
tokenizer = RegexpTokenizer(r'\w+')

def calculate_similarity(skills, job_description, experience_years=None, seniority_level=None):
    """
    Calculate similarity score between resume skills and job description with additional factors
    
    Args:
        skills: List of skills extracted from the resume
        job_description: Job description text
        experience_years: Number of years of experience (if available)
        seniority_level: Seniority level of the candidate (if available)
        
    Returns:
        Dictionary containing similarity score and match category
    """
    try:
        if not skills or not job_description:
            return {
                'score': 0,
                'match_category': 'Low',
                'weighted_score': 0,
                'skill_match_details': {},
                'experience_match': 0,
                'seniority_match': 0,
                'required_experience': 0
            }
        
        # Preprocess job description
        processed_job_desc = preprocess_text(job_description)
        
        # Extract keywords from job description
        job_keywords = extract_keywords_from_job_description(job_description)
        
        # Count matches and calculate skill relevance
        match_count = 0
        matched_skills = {}
        skill_weight = 0.5  # Skills account for 50% of the score
        
        for skill in skills:
            skill_tokens = preprocess_text(skill)
            
            # Check if skill tokens appear in job description
            if all(token in processed_job_desc for token in skill_tokens):
                match_count += 1
                matched_skills[skill] = 'full_match'
                # Give higher weight to skills that are in the top keywords
                if any(token in job_keywords for token in skill_tokens):
                    match_count += 0.5  # Bonus for matching important keywords
                    matched_skills[skill] = 'priority_match'
            # Alternative: check if any token appears
            elif any(token in processed_job_desc for token in skill_tokens):
                match_count += 0.3
                matched_skills[skill] = 'partial_match'
            else:
                matched_skills[skill] = 'no_match'
        
        # Calculate skill similarity percentage
        if len(skills) > 0:
            skill_similarity = (match_count / len(skills)) * 100
        else:
            skill_similarity = 0
            
        # SAP-specific skill handling
        has_sap_skills = any(skill.startswith('SAP') for skill in skills)
        mentioned_in_job = 'sap' in job_description.lower()
        
        if has_sap_skills and mentioned_in_job:
            # Boost SAP skills match for SAP-specific jobs
            sap_match_bonus = 15
            skill_similarity = min(100, skill_similarity + sap_match_bonus)
        
        # Experience accounts for 30% in general roles, but 35% for SAP roles
        experience_weight = 0.35 if has_sap_skills and mentioned_in_job else 0.3
        
        # Adjust score based on experience if provided
        experience_modifier = 0
        req_experience = 0
        if experience_years is not None:
            # Extract experience requirements from job description
            req_experience = extract_experience_requirement(job_description)
            if req_experience:
                # SAP jobs often require more years of experience for the same roles
                if has_sap_skills and mentioned_in_job:
                    # For SAP roles, we can be a bit more lenient
                    if experience_years >= req_experience:
                        experience_modifier = 100
                    elif experience_years >= (req_experience * 0.8):
                        # 80% of required experience is still good for SAP roles
                        experience_modifier = 90
                    else:
                        # Partial match based on how close to requirement
                        experience_modifier = (experience_years / req_experience) * 100
                else:
                    # Standard experience evaluation
                    if experience_years >= req_experience:
                        experience_modifier = 100
                    else:
                        # Partial match based on how close to requirement
                        experience_modifier = (experience_years / req_experience) * 100
            else:
                # No specific experience requirement, so use a standard scale
                if experience_years >= 10:
                    experience_modifier = 100  # Senior level
                elif experience_years >= 5:
                    experience_modifier = 85   # Mid-level
                elif experience_years >= 2:
                    experience_modifier = 70   # Junior level
                else:
                    experience_modifier = 50   # Entry level
        
        # Adjust for seniority - 20% weight for SAP BASIS roles, 15% for other roles
        seniority_modifier = 0
        seniority_weight = 0.20 if has_sap_skills and mentioned_in_job else 0.15  
        
        if seniority_level is not None:
            # Extract seniority requirements from job description
            req_seniority = extract_seniority_level(job_description)
            
            # Map seniority levels to numerical values
            seniority_map = {
                'entry': 1, 
                'junior': 2, 
                'mid': 3,
                'senior': 4, 
                'lead': 5, 
                'manager': 5,
                'director': 6,
                'executive': 7
            }
            
            # Get numerical values
            candidate_level = seniority_map.get(seniority_level.lower(), 0)
            required_level = seniority_map.get(req_seniority.lower(), 0)
            
            if required_level > 0:
                if candidate_level >= required_level:
                    seniority_modifier = 100
                else:
                    # Partial match - more lenient for SAP roles where experience matters more
                    # than formal title
                    if has_sap_skills and mentioned_in_job:
                        # For SAP, being one level below required is still quite good
                        if (required_level - candidate_level) <= 1:
                            seniority_modifier = 85
                        else:
                            seniority_modifier = (candidate_level / required_level) * 100
                    else:
                        # Standard seniority evaluation
                        seniority_modifier = (candidate_level / required_level) * 100
            else:
                # If no specific level is required, assume mid-level
                if candidate_level >= 3:  # Mid or higher
                    seniority_modifier = 100
                else:
                    seniority_modifier = (candidate_level / 3) * 100
        
        # Additional context factors - 5% weight
        context_factors = 0
        context_weight = 0.05
        
        # Check if SAP BASIS admin or similar title is specifically mentioned when this is a SAP BASIS role
        if has_sap_skills and mentioned_in_job and "SAP BASIS" in skills:
            # If the job mentions BASIS admin/administrator/consultant specifically
            if re.search(r'\b(basis\s+adm|basis\s+consultant|basis\s+admin|basis\s+specialist)\b', 
                         job_description.lower()):
                context_factors = 100
            elif "SAP" in job_description and "BASIS" in job_description:
                context_factors = 80
        
        # Calculate weighted score
        weighted_score = (skill_similarity * skill_weight)
        total_weight = skill_weight
        
        if experience_years is not None:
            weighted_score += (experience_modifier * experience_weight)
            total_weight += experience_weight
            
        if seniority_level is not None:
            weighted_score += (seniority_modifier * seniority_weight)
            total_weight += seniority_weight
        
        # Add context weight
        weighted_score += (context_factors * context_weight)
        total_weight += context_weight
            
        # Normalize weighted score
        if total_weight > 0:
            weighted_score = weighted_score / total_weight
        
        # Determine match category
        match_category = 'Low'
        if weighted_score >= 75:
            match_category = 'High'
        elif weighted_score >= 50:
            match_category = 'Medium'
            
        # Final result with detailed breakdown
        result = {
            'score': round(skill_similarity, 1),
            'match_category': match_category,
            'weighted_score': round(weighted_score, 1),
            'skill_match_details': matched_skills,
            'experience_match': round(experience_modifier, 1),
            'seniority_match': round(seniority_modifier, 1),
            'context_match': round(context_factors, 1),
            'required_experience': req_experience
        }
        
        return result
    
    except Exception as e:
        logger.error(f"Error calculating similarity: {str(e)}", exc_info=True)
        return {
            'score': 0,
            'match_category': 'Low',
            'weighted_score': 0,
            'skill_match_details': {},
            'experience_match': 0,
            'seniority_match': 0,
            'required_experience': 0
        }

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
        
        # Tokenize with RegexpTokenizer (removes punctuation)
        tokens = tokenizer.tokenize(text)
        
        # Remove stopwords
        try:
            stop_words = set(stopwords.words('english'))
        except:
            # Use basic stopwords if NLTK download failed
            stop_words = BASIC_STOPWORDS
            
        tokens = [word for word in tokens if word not in stop_words]
        
        # Stem words (simpler than lemmatization but more reliable without wordnet)
        stemmer = PorterStemmer()
        tokens = [stemmer.stem(word) for word in tokens]
        
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

def extract_experience_requirement(job_description):
    """
    Extract years of experience required from job description
    
    Args:
        job_description: Job description text
        
    Returns:
        Integer representing years of experience required, or None if not found
    """
    try:
        # Common patterns for experience requirements
        patterns = [
            r'(\d+)\+?\s*(?:years|yrs)(?:\s*of)?\s*experience',
            r'(\d+)\+?\s*(?:years|yrs)(?:\s*of)?\s*work experience',
            r'experience\s*(?:of|with)?\s*(\d+)\+?\s*(?:years|yrs)',
            r'minimum\s*(?:of)?\s*(\d+)\+?\s*(?:years|yrs)',
            r'at least\s*(\d+)\+?\s*(?:years|yrs)',
            r'(\d+)-(\d+)\s*(?:years|yrs)(?:\s*of)?\s*experience'
        ]
        
        job_text = job_description.lower()
        
        for pattern in patterns:
            matches = re.findall(pattern, job_text)
            if matches:
                # Handle ranges like "3-5 years"
                if isinstance(matches[0], tuple) and len(matches[0]) > 1:
                    # Take the lower end of the range
                    return int(matches[0][0])
                else:
                    # Single value
                    return int(matches[0])
        
        # Default to entry-level if no experience mentioned
        return 0
    
    except Exception as e:
        logger.error(f"Error extracting experience requirement: {str(e)}", exc_info=True)
        return 0

def extract_seniority_level(job_description):
    """
    Extract seniority level from job description
    
    Args:
        job_description: Job description text
        
    Returns:
        String representing the seniority level
    """
    try:
        job_text = job_description.lower()
        
        # SAP-specific seniority terms
        if re.search(r'\b(sap architect|solution architect|technical architect|lead architect|principal consultant)\b', job_text):
            return 'senior'
        elif re.search(r'\b(sap lead|team lead|project lead|senior basis|senior consultant)\b', job_text):
            return 'lead'

        # General seniority indicators
        if re.search(r'\b(chief|cto|cio|ceo|vp|vice president)\b', job_text):
            return 'executive'
        elif re.search(r'\b(director)\b', job_text):
            return 'director'
        elif re.search(r'\b(senior|sr|lead|principal)\b', job_text):
            return 'senior'
        elif re.search(r'\b(manager|management)\b', job_text):
            return 'manager'
        elif re.search(r'\b(mid|intermediate|experienced)\b', job_text):
            return 'mid'
        elif re.search(r'\b(junior|jr)\b', job_text):
            return 'junior'
        elif re.search(r'\b(entry|graduate|trainee|intern)\b', job_text):
            return 'entry'
        
        # For SAP roles, years of experience have different thresholds
        if re.search(r'\b(sap|basis|hana|abap|erp|s/4hana|netweaver)\b', job_text):
            exp_years = extract_experience_requirement(job_description)
            if exp_years >= 10:
                return 'senior'
            elif exp_years >= 7:
                return 'lead'
            elif exp_years >= 4:
                return 'mid'
            elif exp_years >= 2:
                return 'junior'
            else:
                return 'entry'
        else:
            # Standard experience-based seniority for other roles
            exp_years = extract_experience_requirement(job_description)
            if exp_years >= 8:
                return 'senior'
            elif exp_years >= 5:
                return 'mid'
            elif exp_years >= 2:
                return 'junior'
            else:
                return 'entry'
    
    except Exception as e:
        logger.error(f"Error extracting seniority level: {str(e)}", exc_info=True)
        return 'mid'  # Default to mid-level as a safe estimate
