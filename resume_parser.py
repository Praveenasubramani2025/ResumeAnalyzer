import os
import re
import logging
import PyPDF2
import docx
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

def parse_resume_file(file_path):
    """
    Parse a single resume file
    
    Args:
        file_path: Path to the resume file
        
    Returns:
        Dictionary containing parsed resume data
    """
    try:
        file_path = Path(file_path)
        logger.info(f"Processing file: {file_path}")
        
        # Extract text based on file type
        if file_path.suffix.lower() == '.pdf':
            text = extract_text_from_pdf(file_path)
        elif file_path.suffix.lower() in ['.docx', '.doc']:
            text = extract_text_from_docx(file_path)
        elif file_path.suffix.lower() == '.txt':
            text = extract_text_from_txt(file_path)
        else:
            logger.warning(f"Unsupported file type: {file_path}")
            return None
        
        # Parse the text
        parsed_data = extract_data_from_text(text)
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"Error parsing {file_path.name}: {str(e)}", exc_info=True)
        return None

def parse_resumes(folder_path):
    """
    Parse all resume files in the specified folder
    
    Args:
        folder_path: Path to folder containing resume files
        
    Returns:
        List of dictionaries containing parsed resume data
    """
    results = []
    folder = Path(folder_path)
    
    # Supported file extensions
    supported_extensions = ['.pdf', '.docx', '.doc', '.txt']
    
    # Find all resume files in the folder
    for file_path in folder.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            parsed_data = parse_resume_file(file_path)
            if parsed_data:
                parsed_data['file_name'] = file_path.name
                parsed_data['file_path'] = str(file_path)
                results.append(parsed_data)
    
    return results

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        logger.error(f"Error extracting text from PDF {file_path}: {str(e)}", exc_info=True)
        raise
    return text

def extract_text_from_docx(file_path):
    """Extract text from a DOCX file."""
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        logger.error(f"Error extracting text from DOCX {file_path}: {str(e)}", exc_info=True)
        raise
    return text

def extract_text_from_txt(file_path):
    """Extract text from a TXT file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error extracting text from TXT {file_path}: {str(e)}", exc_info=True)
        raise

def extract_data_from_text(text):
    """
    Extract structured data from resume text
    
    Args:
        text: Plain text extracted from resume file
        
    Returns:
        Dictionary containing extracted information
    """
    # Initialize the result dictionary
    result = {
        'name': extract_name(text),
        'email': extract_email(text),
        'phone': extract_phone(text),
        'skills': extract_skills(text),
        'experience_years': extract_experience_years(text),
        'seniority_level': determine_seniority_level(text)
    }
    
    return result

def extract_name(text):
    """Extract candidate name from text."""
    # This is a simplified approach. In a real scenario, we would use NLP for better name extraction
    lines = text.split('\n')
    
    # Consider first non-empty line as name (simplified approach)
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if line and len(line) < 50:  # Avoid very long lines
            # Skip lines that are likely email addresses or phone numbers
            if '@' not in line and not re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', line):
                return line
    
    return "Unknown"

def extract_email(text):
    """Extract email addresses from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    
    return matches[0] if matches else ""

def extract_phone(text):
    """Extract phone numbers from text."""
    # Define common phone patterns
    patterns = [
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 123-456-7890
        r'\b\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}\b',  # (123) 456-7890
        r'\b\+\d{1,2}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'  # +1 123-456-7890
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            return matches[0]
    
    return ""

def extract_skills(text):
    """Extract skills from text."""
    # List of common technical skills
    common_skills = [
        # Programming Languages
        "Python", "Java", "JavaScript", "C++", "C#", "PHP", "Ruby", "Swift", "Go", "Kotlin", "R",
        "TypeScript", "Scala", "Perl", "Rust", "MATLAB", "Groovy", "Objective-C", "Bash", "PowerShell",
        
        # Web Development
        "HTML", "CSS", "React", "Angular", "Vue.js", "Node.js", "Express", "Django", "Flask", "Laravel",
        "Ruby on Rails", "ASP.NET", "Spring", "jQuery", "Bootstrap", "Sass", "LESS", "WordPress", "Redux",
        
        # Mobile Development
        "Android", "iOS", "React Native", "Flutter", "Xamarin", "Ionic", "Swift UI", "Kotlin Multiplatform",
        
        # Databases
        "SQL", "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle", "MS SQL Server", "Redis", "MariaDB",
        "NoSQL", "Firebase", "Cassandra", "DynamoDB", "Elasticsearch", "Neo4j",
        
        # DevOps & Cloud
        "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Jenkins", "Git", "GitHub", "Bitbucket", 
        "CI/CD", "Terraform", "Ansible", "Chef", "Puppet", "Vagrant", "Prometheus", "Grafana", "ELK Stack",
        
        # Data Science & Machine Learning
        "TensorFlow", "PyTorch", "scikit-learn", "Pandas", "NumPy", "SciPy", "Keras", "OpenCV", "NLTK",
        "spaCy", "Machine Learning", "Deep Learning", "AI", "Data Analysis", "Data Visualization",
        "Big Data", "Hadoop", "Spark", "NLP", "Computer Vision", "Reinforcement Learning",
        
        # Software Engineering
        "OOP", "Design Patterns", "Agile", "Scrum", "Kanban", "UML", "Software Architecture", "Microservices",
        "RESTful API", "GraphQL", "SOAP", "RPC", "Unit Testing", "Integration Testing", "TDD", "BDD",
        
        # Other Technical Skills
        "Linux", "Unix", "Windows", "macOS", "Networking", "Security", "Blockchain", "Cryptography",
        "AR/VR", "IoT", "Game Development", "Unity", "Unreal Engine", "Embedded Systems", "Robotics"
    ]
    
    found_skills = []
    
    # Search for each skill in the text
    for skill in common_skills:
        # Create a regex pattern that finds whole words only
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            found_skills.append(skill)
    
    return found_skills

def extract_experience_years(text):
    """
    Extract total years of experience from resume text
    
    Args:
        text: Plain text extracted from resume file
        
    Returns:
        Integer representing years of experience
    """
    try:
        # Common patterns for experience in resumes
        patterns = [
            r'(\d+)\+?\s*(?:years|yrs)(?:\s*of)?\s*(?:total|overall)?\s*experience',
            r'(?:total|overall)\s*(?:of)?\s*(\d+)\+?\s*(?:years|yrs)',
            r'(?:worked|working)\s*(?:for)?\s*(\d+)\+?\s*(?:years|yrs)',
            r'(\d+)\+?\s*(?:years|yrs)\s*(?:in|of experience in)'
        ]
        
        experience_text = text.lower()
        
        all_years = []
        
        # Find all mentions of years of experience
        for pattern in patterns:
            matches = re.findall(pattern, experience_text)
            if matches:
                for match in matches:
                    try:
                        years = int(match)
                        all_years.append(years)
                    except ValueError:
                        pass
        
        # If we found experience years, use the highest number
        if all_years:
            return max(all_years)
        
        # Try to infer from employment history
        experience = estimate_experience_from_employment(text)
        if experience > 0:
            return experience
        
        # Default to entry-level if no experience found
        return 1
    
    except Exception as e:
        logger.error(f"Error extracting experience years: {str(e)}", exc_info=True)
        return 1

def estimate_experience_from_employment(text):
    """
    Estimate years of experience by analyzing employment history
    
    Args:
        text: Resume text
        
    Returns:
        Estimated years of experience
    """
    try:
        # Look for date ranges (e.g., 2018-2022, 2018 - Present, etc.)
        date_patterns = [
            r'(\d{4})\s*(?:-|to|–|—)\s*(\d{4}|\bpresent\b|\bcurrent\b)',
            r'(\d{2}/\d{4})\s*(?:-|to|–|—)\s*(\d{2}/\d{4}|\bpresent\b|\bcurrent\b)',
            r'(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4})\s*(?:-|to|–|—)\s*(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}|\bpresent\b|\bcurrent\b)'
        ]
        
        total_years = 0
        current_year = 2025  # Using current year
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                start, end = match
                
                # Extract start year
                start_year = None
                if re.match(r'\d{4}', start):
                    start_year = int(re.search(r'\d{4}', start).group())
                elif '/' in start:
                    start_year = int(start.split('/')[-1])
                
                # Extract end year
                end_year = None
                if re.match(r'\d{4}', end):
                    end_year = int(re.search(r'\d{4}', end).group())
                elif '/' in end:
                    end_year = int(end.split('/')[-1])
                elif 'present' in end or 'current' in end:
                    end_year = current_year
                
                # Calculate years for this position if we have both dates
                if start_year and end_year:
                    years = end_year - start_year
                    if years > 0 and years < 50:  # Sanity check
                        total_years += years
        
        return total_years if total_years > 0 else 1
    
    except Exception as e:
        logger.error(f"Error estimating experience from employment: {str(e)}", exc_info=True)
        return 1

def determine_seniority_level(text):
    """
    Determine the seniority level based on resume text
    
    Args:
        text: Resume text
        
    Returns:
        String indicating seniority level
    """
    try:
        text_lower = text.lower()
        
        # Check for explicit seniority mentions in job titles
        if re.search(r'\b(cto|cio|ceo|chief|vp|vice president)\b', text_lower):
            return 'executive'
        elif re.search(r'\b(director)\b', text_lower):
            return 'director'
        elif re.search(r'\b(senior|sr|lead|principal)\b', text_lower):
            return 'senior'
        elif re.search(r'\b(manager)\b', text_lower):
            return 'manager'
        elif re.search(r'\b(mid|intermediate)\b', text_lower):
            return 'mid'
        elif re.search(r'\b(junior|jr)\b', text_lower):
            return 'junior'
        elif re.search(r'\b(trainee|intern|graduate)\b', text_lower):
            return 'entry'
        
        # Determine by years of experience
        years = extract_experience_years(text)
        if years >= 10:
            return 'senior'
        elif years >= 7:
            return 'lead'
        elif years >= 5:
            return 'mid'
        elif years >= 2:
            return 'junior'
        else:
            return 'entry'
    
    except Exception as e:
        logger.error(f"Error determining seniority level: {str(e)}", exc_info=True)
        return 'mid'  # Default to mid-level
