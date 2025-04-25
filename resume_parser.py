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
    # Log the first 1000 characters of text for debugging
    logger.debug(f"Extracting email from text starting with: {text[:1000]}")
    
    # More comprehensive email pattern
    email_patterns = [
        # Standard email pattern
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        # Email with "mailto:" prefix
        r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
        # Email with various prefixes like "Email:", "E-mail:", "Mail:", etc.
        r'(?:E-?mail|Mail|Electronic Mail|Contact|Email Address)(?:[\s:]*|[\s]*at[\s]+)([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
        # Email in brackets, parentheses, or with HTML-like formatting
        r'[\[\(]([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})[\]\)]',
        # Email with word boundaries, allowing more relaxed matching
        r'(?:\s|^|\()([A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})(?:\s|$|\))',
        # Email following specific labels in resumes
        r'(?:Contact|Email|E-mail|Mail|Communication)[\s:-]*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
    ]
    
    # First try the more precise patterns
    for pattern in email_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # If we have a capture group, we'll get the email in group 1
            if isinstance(matches[0], tuple) and matches[0]:
                email = matches[0][0]
            else:
                email = matches[0]
                
            # Quick validation of the extracted email
            if isinstance(email, str) and '@' in email and '.' in email.split('@')[1] and len(email) > 5:
                logger.debug(f"Found email: {email}")
                return email
    
    # Try looking for text like "Email: someone at domain dot com"
    obfuscated_patterns = [
        r'(?:email|e-mail|contact|mail)(?::|at|\s)+([a-zA-Z0-9._%+-]+)\s+(?:at|@)\s+([a-zA-Z0-9.-]+)\s+(?:dot|\.)\s+([a-zA-Z]{2,})',
        r'([a-zA-Z0-9._%+-]+)\s+(?:at|@)\s+([a-zA-Z0-9.-]+)\s+(?:dot|\.)\s+([a-zA-Z]{2,})'
    ]
    
    for pattern in obfuscated_patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            for match in matches:
                if len(match) >= 3:
                    # Reconstruct email from parts
                    email = f"{match[0]}@{match[1]}.{match[2]}"
                    logger.debug(f"Found obfuscated email: {email}")
                    return email
    
    # If we got here, we couldn't find an email
    logger.warning(f"No email found in text")
    return ""

def extract_phone(text):
    """Extract phone numbers from text."""
    # Log the first 1000 characters of text for debugging
    logger.debug(f"Extracting phone from text starting with: {text[:1000]}")
    
    # Define common phone patterns - expanded for more formats
    patterns = [
        # With prefix like "Tel:" or "Phone:" or "Contact:" - these have higher priority
        r'(?:Tel|Telephone|Phone|Mobile|Cell|Contact|Call)(?:[.:\s-]|\sat\s)+\s*(\+?\d[\d\s\(\).-]{7,})',
        r'(?:Tel|Telephone|Phone|Mobile|Cell|Contact|Call)(?:[.:\s-]|\sat\s)+\s*(\(\d{3}\)[\s.-]?\d{3}[\s.-]?\d{4})',
        r'(?:Tel|Telephone|Phone|Mobile|Cell|Contact)[.:\s-]+\s*(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})',
        
        # International formats with country codes
        r'\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,4}\b',  # +1 123-456-7890 or +44 20 1234 5678
        r'\b\+\d{1,3}[-.\s]?\(\d{1,4}\)[-.\s]?\d{1,4}[-.\s]?\d{1,4}\b', # +1 (123) 456-7890
        
        # Standard US/Canada formats
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 123-456-7890
        r'\b\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}\b',  # (123) 456-7890
        
        # Common formats used in SAP/IT resumes
        r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b', # 123-456-7890 with explicit separator
        r'\b\d{3}[.]\d{3}[.]\d{4}\b', # 123.456.7890 with dots
        r'\b\d{4}[-.\s]\d{3}[-.\s]\d{3}\b', # 1234 567 890 (some international formats)
        
        # Last resort - any 10-digit number that could be a phone number
        r'(?<![0-9])\d{10}(?![0-9])', # 1234567890 (not preceded or followed by a digit)
    ]
    
    # First try looking for phones with context - these are most reliable
    for pattern in patterns[:3]:  # The patterns with prefixes
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                # Clean up the result
                phone = match.strip()
                # Validate that this looks like a phone number
                if re.search(r'\d{3}.*\d{3}.*\d{4}', phone):
                    logger.debug(f"Found phone with context: {phone}")
                    return phone
    
    # Then try all patterns
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                # Clean up the result - if it's a tuple, take the first element
                if isinstance(match, tuple):
                    phone = match[0].strip()
                else:
                    phone = match.strip()
                    
                # Basic validation - must contain at least 10 digits
                digit_count = sum(c.isdigit() for c in phone)
                if digit_count >= 10:
                    logger.debug(f"Found phone number: {phone}")
                    return phone
    
    # Look for numbers near phone-related terms
    phone_terms = ["phone", "mobile", "cell", "tel", "contact", "call me", "reach me"]
    for term in phone_terms:
        # Find the term and look for numbers nearby
        term_match = re.search(f"\\b{term}\\b", text.lower())
        if term_match:
            # Look for numbers within 50 characters of the term
            start_pos = max(0, term_match.start() - 20)
            end_pos = min(len(text), term_match.end() + 30)
            nearby_text = text[start_pos:end_pos]
            
            # Try to find numbers in this segment
            number_matches = re.findall(r'\b\d[\d\s\(\).-]{7,15}\b', nearby_text)
            for num in number_matches:
                # Basic validation - must contain at least 10 digits
                digit_count = sum(c.isdigit() for c in num)
                if digit_count >= 10:
                    logger.debug(f"Found phone number near '{term}': {num}")
                    return num
    
    # If we got here, we couldn't find a phone number
    logger.warning(f"No phone number found in text")
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
        "AR/VR", "IoT", "Game Development", "Unity", "Unreal Engine", "Embedded Systems", "Robotics",
        
        # SAP Skills
        "SAP", "SAP BASIS", "BASIS", "SAP HANA", "HANA", "SAP ABAP", "ABAP", "SAP ERP", "ERP", 
        "SAP R/3", "SAP S/4HANA", "S/4HANA", "SAP MM", "MM", "SAP SD", "SD", "SAP PP", "PP", 
        "SAP FI", "FI", "SAP CO", "CO", "SAP HCM", "HCM", "SAP BW", "BW", "SAP BI", "BI", 
        "SAP CRM", "CRM", "SAP SRM", "SRM", "SAP SCM", "SCM", "SAP MDM", "MDM", "SAP PLM", "PLM",
        "SAP Solution Manager", "Solution Manager", "Solman", "SAP Fiori", "Fiori", "SAP UI5", "UI5",
        "SAP NetWeaver", "NetWeaver", "SAP BODS", "BODS", "SAP PI", "PI", "SAP PO", "PO", 
        "SAP BPC", "BPC", "SAP GRC", "GRC", "SAP ADS", "ADS", "SAP SLT", "SLT", "SAP FICO", "FICO",
        "SAPUI5", "SAP GUI", "SAP Portal", "SAP BTP", "BTP", "SAP CAR", "CAR",
        "SAP Landscape", "SAP Authorizations", "SAP Security", "SAP Administration", "SAP Monitoring",
        "SAP System Copy", "SAP Migration", "SAP Upgrade", "SAP Patches", "SAP Troubleshooting",
        "SAP Performance", "SAP Tuning", "SAP Transport", "SAP Backup", "SAP Recovery"
    ]
    
    found_skills = []
    
    # Search for each skill in the text
    for skill in common_skills:
        # Create a regex pattern that finds whole words only
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            found_skills.append(skill)
    
    # Special case handling for SAP BASIS
    if "BASIS" in found_skills and "SAP" in found_skills and "SAP BASIS" not in found_skills:
        found_skills.append("SAP BASIS")
    
    # If we found very few skills, try to extract from paragraphs
    if len(found_skills) < 3:
        # Extract skills from bullet point lists and paragraphs
        skill_sections = re.findall(r'(?:skills|expertise|proficiency|knowledge|competenc(?:y|ies))[:\s]+(.*?)(?:\n\n|\Z)', 
                               text.lower(), re.DOTALL)
        
        if skill_sections:
            for section in skill_sections:
                # Split by common separators and clean up
                potential_skills = re.split(r'[,;•|\n]', section)
                for skill_item in potential_skills:
                    skill_item = skill_item.strip()
                    if len(skill_item) > 2 and len(skill_item) < 50:  # Reasonable length for a skill
                        # Try to match with known skills
                        for skill in common_skills:
                            if skill.lower() in skill_item and skill not in found_skills:
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
        # Common patterns for experience in resumes - expanded with more variants
        patterns = [
            # General experience patterns
            r'(\d+)[\+]?\s*(?:years|yrs|year)(?:\s*of)?\s*(?:total|overall|professional|relevant|industry)?\s*experience',
            r'(?:total|overall|professional)\s*(?:of)?\s*(\d+)[\+]?\s*(?:years|yrs|year)\s*(?:experience|in)?',
            r'(?:worked|working|experience)\s*(?:for|of)?\s*(\d+)[\+]?\s*(?:years|yrs|year)',
            r'(\d+)[\+]?\s*(?:years|yrs|year)\s*(?:in|of experience in|experience with)',
            
            # IT/SAP specific experience patterns
            r'(?:sap|it|technical)\s*(?:experience|professional)(?:\s*of)?\s*(\d+)[\+]?\s*(?:years|yrs|year)',
            r'(\d+)[\+]?\s*(?:years|yrs|year)\s*(?:of)?\s*(?:sap|basis|it|technical)\s*experience',
            r'experience\s*(?:with|in)\s*(?:sap|basis)(?:\s*for)?\s*(\d+)[\+]?\s*(?:years|yrs|year)',
            
            # Experience with "+" mentions
            r'(\d+)\+\s*(?:years|yrs|year)',
            
            # Professional summary with years
            r'(?:professional with|consultant with|specialist with)\s*(\d+)[\+]?\s*(?:years|yrs|year)',
        ]
        
        experience_text = text.lower()
        
        all_years = []
        
        # Find all mentions of years of experience
        for pattern in patterns:
            matches = re.findall(pattern, experience_text)
            if matches:
                for match in matches:
                    try:
                        if isinstance(match, tuple):
                            for submatch in match:
                                if submatch.isdigit():
                                    years = int(submatch)
                                    all_years.append(years)
                        else:
                            years = int(match)
                            all_years.append(years)
                    except (ValueError, TypeError):
                        pass
        
        # If we found experience years, use the highest number
        if all_years:
            return max(all_years)
        
        # Try to infer from employment history
        experience = estimate_experience_from_employment(text)
        if experience > 0:
            return experience
        
        # Check for career-spanning terms that suggest extensive experience
        if any(term in experience_text for term in 
               ['senior consultant', 'principal consultant', 'lead consultant', 
                'senior basis', 'chief', 'head of', 'director']):
            return 10  # Default to senior level when senior-related terms are found
        
        # Default to mid-level if no experience found but technical terms present
        if any(term in experience_text for term in 
               ['sap', 'basis', 'hana', 'abap', 'netweaver', 'fiori']):
            return 5
            
        # Default to entry-level if nothing found
        return 1
    
    except Exception as e:
        logger.error(f"Error extracting experience years: {str(e)}", exc_info=True)
        return 3  # Default to junior level in case of errors

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
            # YYYY-YYYY or YYYY-Present
            r'(\d{4})\s*(?:-|to|–|—)\s*(\d{4}|\bpresent\b|\bcurrent\b|\bnow\b)',
            # MM/YYYY-MM/YYYY
            r'(\d{1,2}/\d{4})\s*(?:-|to|–|—)\s*(\d{1,2}/\d{4}|\bpresent\b|\bcurrent\b|\bnow\b)',
            # Month YYYY - Month YYYY
            r'(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4})\s*(?:-|to|–|—)\s*(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}|\bpresent\b|\bcurrent\b|\bnow\b)',
            # For SAP resumes: look for common project duration formats
            r'(?:project|contract).*?(\d{4})\s*(?:-|to|–|—)\s*(\d{4}|\bpresent\b|\bcurrent\b|\bnow\b)'
        ]
        
        # Check for indicators of single-company long tenure 
        experience_text = text.lower()
        
        # If we see phrases like "12 years at [company]" or "with [company] since 2010"
        long_tenure_patterns = [
            r'(\d+)\s*(?:years|yrs|year)\s*(?:at|with)\s*\w+',
            r'(?:since|from)\s*(\d{4})\s*(?:at|with|to present)',
            r'(?:joined)\s*\w+\s*(?:in)\s*(\d{4})'
        ]
        
        for pattern in long_tenure_patterns:
            matches = re.findall(pattern, experience_text)
            if matches:
                for match in matches:
                    try:
                        # Direct year count
                        if len(match) <= 4:  # It's likely a year, not a count
                            if int(match) > 1900:  # It's definitely a year
                                years = 2025 - int(match)
                                if years > 0 and years < 50:
                                    return years
                            else:
                                # It's a count of years
                                return int(match)
                    except (ValueError, TypeError):
                        pass
                        
        # Standard date range processing
        total_years = 0
        current_year = 2025  # Using current year
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    start, end = match[0], match[1]
                    
                    # Extract start year
                    start_year = None
                    if re.search(r'\d{4}', start):
                        year_match = re.search(r'\d{4}', start)
                        if year_match:
                            start_year = int(year_match.group())
                    elif '/' in start and len(start.split('/')) > 1:
                        try:
                            start_year = int(start.split('/')[-1])
                        except (ValueError, IndexError):
                            pass
                    
                    # Extract end year
                    end_year = None
                    if re.search(r'\d{4}', end):
                        year_match = re.search(r'\d{4}', end) 
                        if year_match:
                            end_year = int(year_match.group())
                    elif '/' in end and len(end.split('/')) > 1:
                        try:
                            end_year = int(end.split('/')[-1])
                        except (ValueError, IndexError):
                            pass
                    elif any(word in end.lower() for word in ['present', 'current', 'now', 'till date', 'to date']):
                        end_year = current_year
                    
                    # Calculate years for this position if we have both dates
                    if start_year and end_year and start_year < end_year:
                        years = end_year - start_year
                        if years > 0 and years < 50:  # Sanity check
                            total_years += years
        
        # If total experience exceeds 30 years, it might be an error - cap it
        if total_years > 30:
            return 30
            
        return total_years if total_years > 0 else 5  # Default to mid-level experience
    
    except Exception as e:
        logger.error(f"Error estimating experience from employment: {str(e)}", exc_info=True)
        return 5  # Default to mid-level in case of errors

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
