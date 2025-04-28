import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
import pandas as pd
import tempfile
import json
from pathlib import Path
import shutil
import io
import uuid
import werkzeug
from resume_parser import parse_resume_file
from similarity_calculator import calculate_similarity

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    """Render the main page of the application."""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    """Process uploaded resume files and job description input."""
    try:
        # Get job description
        job_description = request.form.get('job_description', '')
        
        # Check if files are uploaded
        if 'resume_files' not in request.files:
            flash('No files uploaded', 'danger')
            return redirect(url_for('index'))
        
        files = request.files.getlist('resume_files')
        
        # Validate files
        if not files or len(files) == 0 or files[0].filename == '':
            flash('No files selected', 'danger')
            return redirect(url_for('index'))
        
        # Create a temporary folder for processing
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(uuid.uuid4()))
        os.makedirs(upload_dir, exist_ok=True)
        
        parsed_resumes = []
        
        # Save and process each file
        for file in files:
            if file and file.filename != '':
                try:
                    # Check if file type is allowed
                    filename = werkzeug.utils.secure_filename(file.filename)
                    file_path = os.path.join(upload_dir, filename)
                    
                    # Save the file
                    file.save(file_path)
                    
                    # Parse the resume file
                    parsed_data = parse_resume_file(file_path)
                    
                    if parsed_data:
                        parsed_data['file_name'] = filename
                        parsed_data['file_path'] = file_path
                        parsed_resumes.append(parsed_data)
                        logger.info(f"Successfully parsed: {filename}")
                    
                except Exception as e:
                    logger.error(f"Error processing file {file.filename}: {str(e)}", exc_info=True)
                    # Continue processing other files
        
        # Clean up after processing
        try:
            shutil.rmtree(upload_dir)
        except Exception as e:
            logger.warning(f"Could not remove temporary directory: {str(e)}")
        
        if not parsed_resumes:
            flash('No valid resume files were found in the upload', 'warning')
            return redirect(url_for('index'))
        
        # Calculate similarity if job description is provided
        if job_description:
            for resume in parsed_resumes:
                # Get experience and seniority for more accurate scoring
                experience_years = resume.get('experience_years', None)
                seniority_level = resume.get('seniority_level', None)
                
                # Calculate similarity with additional factors
                similarity_result = calculate_similarity(
                    resume.get('skills', []), 
                    job_description,
                    experience_years,
                    seniority_level
                )
                
                # Store the results
                resume['similarity_score'] = similarity_result.get('score', 0)
                resume['match_category'] = similarity_result.get('match_category', 'Low')
                resume['weighted_score'] = similarity_result.get('weighted_score', 0)
        else:
            for resume in parsed_resumes:
                resume['similarity_score'] = 'N/A'
                resume['match_category'] = 'N/A'
                resume['weighted_score'] = 'N/A'
        
        # Store parsed data in session for display
        session['parsed_resumes'] = parsed_resumes
        session['job_description'] = job_description
        
        return redirect(url_for('results'))
    
    except Exception as e:
        logger.error(f"Error processing resumes: {str(e)}", exc_info=True)
        flash(f'An error occurred while processing resumes: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/results')
def results():
    """Display the parsing results."""
    parsed_resumes = session.get('parsed_resumes', [])
    job_description = session.get('job_description', '')
    
    if not parsed_resumes:
        flash('No results to display. Please upload resume files for parsing.', 'warning')
        return redirect(url_for('index'))
    
    return render_template('results.html', resumes=parsed_resumes, job_description=job_description)

@app.route('/download_csv')
def download_csv():
    """Download parsed resume data as CSV."""
    parsed_resumes = session.get('parsed_resumes', [])
    
    if not parsed_resumes:
        flash('No data to download', 'warning')
        return redirect(url_for('results'))
    
    try:
        # Prepare data for CSV export
        data = []
        for resume in parsed_resumes:
            # Create a formatted contact string
            contact_info = f"Email: {resume.get('email', 'N/A')}, Phone: {resume.get('phone', 'N/A')}"
            
            # Create a formatted skills string, sorted alphabetically
            skills_list = sorted(resume.get('skills', []))
            skills_str = ', '.join(skills_list)
            
            row = {
                'Name': resume.get('name', 'Unknown'),
                'Email': resume.get('email', ''),
                'Phone': resume.get('phone', ''),
                'Contact Info': contact_info,
                'Experience (Years)': resume.get('experience_years', 'N/A'),
                'Seniority Level': resume.get('seniority_level', 'N/A'),
                'Skills': skills_str,
                'Skills Count': len(resume.get('skills', [])),
                'Similarity Score': resume.get('similarity_score', 'N/A'),
                'Match Category': resume.get('match_category', 'N/A'),
                'Weighted Score': resume.get('weighted_score', 'N/A'),
                'File Name': resume.get('file_name', '')
            }
            data.append(row)
        
        # Create a DataFrame
        df = pd.DataFrame(data)
        
        # Create a string buffer
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        
        # Create a bytes buffer from the string buffer
        bytes_buffer = io.BytesIO(buffer.getvalue().encode('utf-8'))
        bytes_buffer.seek(0)
        
        # Get timestamp for filename
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return send_file(
            bytes_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'resume_parsing_results_{timestamp}.csv'
        )
    
    except Exception as e:
        logger.error(f"Error downloading CSV: {str(e)}", exc_info=True)
        flash(f'An error occurred while generating CSV: {str(e)}', 'danger')
        return redirect(url_for('results'))

@app.route('/download_json')
def download_json():
    """Download parsed resume data as JSON."""
    parsed_resumes = session.get('parsed_resumes', [])
    
    if not parsed_resumes:
        flash('No data to download', 'warning')
        return redirect(url_for('results'))
    
    try:
        # Create a bytes buffer
        buffer = io.BytesIO()
        
        # Get timestamp for filename
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Add a metadata field to the JSON
        export_data = {
            "metadata": {
                "export_date": datetime.datetime.now().isoformat(),
                "resume_count": len(parsed_resumes),
                "version": "1.0"
            },
            "resumes": parsed_resumes
        }
        
        buffer.write(json.dumps(export_data, indent=4).encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'resume_parsing_results_{timestamp}.json'
        )
    
    except Exception as e:
        logger.error(f"Error downloading JSON: {str(e)}", exc_info=True)
        flash(f'An error occurred while generating JSON: {str(e)}', 'danger')
        return redirect(url_for('results'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
