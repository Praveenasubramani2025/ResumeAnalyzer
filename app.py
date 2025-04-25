import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
import pandas as pd
import tempfile
import json
from pathlib import Path
import shutil
import io

from resume_parser import parse_resumes
from similarity_calculator import calculate_similarity

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

@app.route('/')
def index():
    """Render the main page of the application."""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    """Process the folder path and job description input."""
    try:
        folder_path = request.form.get('folder_path')
        job_description = request.form.get('job_description')
        
        # Validate inputs
        if not folder_path:
            flash('Please provide a folder path', 'danger')
            return redirect(url_for('index'))
        
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            flash(f'Folder path {folder_path} does not exist or is not a directory', 'danger')
            return redirect(url_for('index'))
        
        # Parse resumes
        parsed_resumes = parse_resumes(folder_path)
        
        if not parsed_resumes:
            flash('No valid resume files found in the specified folder', 'warning')
            return redirect(url_for('index'))
        
        # Calculate similarity if job description is provided
        if job_description:
            for resume in parsed_resumes:
                resume['similarity_score'] = calculate_similarity(resume.get('skills', []), job_description)
        else:
            for resume in parsed_resumes:
                resume['similarity_score'] = 'N/A'
        
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
        flash('No results to display. Please submit a folder for parsing.', 'warning')
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
            row = {
                'Name': resume.get('name', 'Unknown'),
                'Email': resume.get('email', ''),
                'Phone': resume.get('phone', ''),
                'Skills': ', '.join(resume.get('skills', [])),
                'Similarity Score': resume.get('similarity_score', 'N/A'),
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
        
        return send_file(
            bytes_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name='resume_parsing_results.csv'
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
        buffer.write(json.dumps(parsed_resumes, indent=4).encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name='resume_parsing_results.json'
        )
    
    except Exception as e:
        logger.error(f"Error downloading JSON: {str(e)}", exc_info=True)
        flash(f'An error occurred while generating JSON: {str(e)}', 'danger')
        return redirect(url_for('results'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
