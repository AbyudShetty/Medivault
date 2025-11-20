from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytesseract
from PIL import Image
import re
import requests
import json
import easyocr
from google.cloud import vision
import io

app = Flask(__name__)
app.secret_key = 'medivault_secret_key'

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Initialize EasyOCR Reader
print("ðŸ”„ Initializing EasyOCR...")
try:
    reader = easyocr.Reader(['en'], gpu=False)
    print("âœ… EasyOCR initialized!")
except Exception as e:
    reader = None
    print(f"âš ï¸ EasyOCR initialization failed: {e}")

# Google Vision API setup
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'google-vision-key.json')
if os.path.exists(CREDENTIALS_PATH):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_PATH
    try:
        vision_client = vision.ImageAnnotatorClient()
        print("âœ… Google Vision API initialized!")
    except Exception as e:
        print(f"âš ï¸ Google Vision init error: {e}")
        vision_client = None
else:
    print("âš ï¸ Google Vision credentials not found")
    vision_client = None

# Groq API Configuration
GROQ_API_KEY = "groq api key here" 
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Database connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="sql123",
    database="MediVault",
    ssl_disabled=True
)
cursor = db.cursor(dictionary=True)

# Upload folder configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_triple_ocr(image_path):
    """Extract text using ALL THREE OCR methods"""
    tesseract_text = ""
    easyocr_text = ""
    google_vision_text = ""
    
    try:
        print("ðŸ” Method 1: Tesseract OCR...")
        image = Image.open(image_path)
        tesseract_text = pytesseract.image_to_string(image)
        print(f"   âœ… Extracted {len(tesseract_text)} characters")
    except Exception as e:
        print(f"   âš ï¸ Error: {e}")
    
    try:
        if reader is not None:
            print("ðŸ” Method 2: EasyOCR...")
            result = reader.readtext(image_path, detail=0)
            easyocr_text = '\n'.join(result)
            print(f"   âœ… Extracted {len(easyocr_text)} characters")
    except Exception as e:
        print(f"   âš ï¸ Error: {e}")
    
    try:
        if vision_client is not None:
            print("ðŸ” Method 3: Google Vision API...")
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            image = vision.Image(content=content)
            response = vision_client.document_text_detection(image=image)
            if response.full_text_annotation:
                google_vision_text = response.full_text_annotation.text
                print(f"   âœ… Extracted {len(google_vision_text)} characters")
    except Exception as e:
        print(f"   âš ï¸ Error: {e}")
    
    return tesseract_text, easyocr_text, google_vision_text

def parse_prescription_with_groq_fusion(tesseract_text, easyocr_text, google_vision_text):
    """Use Groq AI to intelligently fuse ALL THREE OCR results"""
    try:
        print("ðŸ¤– Sending ALL THREE OCR results to Groq AI...")
        
        prompt = f"""You are an expert medical prescription parser with THREE OCR extractions of the SAME prescription.

TESSERACT OCR:
{tesseract_text}

EASYOCR:
{easyocr_text}

GOOGLE VISION API:
{google_vision_text}

Combine the best from each OCR. Return ONLY valid JSON:
{{
    "doctor_name": "name or empty",
    "date": "DD/MM/YYYY or empty",
    "medicines": [
        {{
            "name": "medicine name",
            "dosage": "100mg or empty",
            "frequency": "BID/TID/QD or empty",
            "duration": "5 days or empty"
        }}
    ]
}}

Rules: Doctor names from Google Vision, medicine names from EasyOCR, dosages from Tesseract. Fix typos. Return ONLY JSON."""

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.05,
            "max_tokens": 2000
        }
        
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=45)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            json_match = re.search(r'\{[\s\S]*\}', ai_response)
            if json_match:
                parsed_data = json.loads(json_match.group())
                print(f"âœ… AI fused: {len(parsed_data.get('medicines', []))} medicines")
                return parsed_data
        return {"doctor_name": "", "date": "", "medicines": []}
    except Exception as e:
        print(f"âŒ Groq error: {e}")
        return {"doctor_name": "", "date": "", "medicines": []}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        try:
            cursor.execute("INSERT INTO user (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
            db.commit()
            user_id = cursor.lastrowid
            session['user_id'] = user_id
            session['user_name'] = name
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard'))
        except mysql.connector.Error as err:
            flash(f'Error: {err.msg}', 'danger')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get prescriptions (JOIN query with medicines)
    cursor.execute("""
        SELECT p.prescription_id, p.issue, p.doctor_name, p.prescription_date, 
               p.file_path, p.created_at, p.medicine_count,
               COUNT(pm.pm_id) as actual_medicine_count
        FROM prescription p
        LEFT JOIN prescription_medication pm ON p.prescription_id = pm.prescription_id
        WHERE p.user_id = %s
        GROUP BY p.prescription_id
        ORDER BY p.created_at DESC
    """, (session['user_id'],))
    prescriptions = cursor.fetchall()
    
    # Call stored procedure for summary statistics (AGGREGATE)
    cursor.callproc('GetPrescriptionSummary', [session['user_id']])
    for result in cursor.stored_results():
        stats = result.fetchone()

    cursor.execute("SELECT GetTotalMedicinesUsed(%s) as total_medicines", (session['user_id'],))
    function_result = cursor.fetchone()
    if stats:
        stats['total_medicines'] = function_result['total_medicines'] if function_result else 0
    
    return render_template('dashboard.html', 
                         name=session['user_name'], 
                         prescriptions=prescriptions,
                         stats=stats if stats else {'total_prescriptions': 0, 'total_doctors': 0, 'active_months': 0})

@app.route('/analytics')
def analytics():
    """Analytics dashboard with AGGREGATE queries"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Aggregate query 1: Prescriptions per month
    cursor.execute("""
        SELECT 
            DATE_FORMAT(created_at, '%Y-%m') as month,
            COUNT(*) as count
        FROM prescription
        WHERE user_id = %s
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    """, (session['user_id'],))
    monthly_stats = cursor.fetchall()
    
    # Call stored procedure for medicine statistics
    cursor.callproc('GetMedicineStats', [session['user_id']])
    for result in cursor.stored_results():
        medicine_stats = result.fetchall()
    
    # Aggregate query 2: Most common issues
    cursor.execute("""
        SELECT issue, COUNT(*) as count
        FROM prescription
        WHERE user_id = %s
        GROUP BY issue
        ORDER BY count DESC
        LIMIT 5
    """, (session['user_id'],))
    top_issues = cursor.fetchall()
    
    # NESTED QUERY: Find prescriptions with above-average medicine count
    cursor.execute("""
        SELECT 
            p.prescription_id,
            p.issue,
            p.doctor_name,
            p.prescription_date,
            COUNT(pm.pm_id) as medicine_count
        FROM prescription p
        INNER JOIN prescription_medication pm ON p.prescription_id = pm.prescription_id
        WHERE p.user_id = %s
        AND p.prescription_id IN (
            SELECT p2.prescription_id
            FROM prescription p2
            INNER JOIN prescription_medication pm2 ON p2.prescription_id = pm2.prescription_id
            WHERE p2.user_id = %s
            GROUP BY p2.prescription_id
            HAVING COUNT(pm2.pm_id) >= (
                SELECT AVG(med_count) FROM (
                    SELECT COUNT(pm3.pm_id) as med_count
                    FROM prescription p3
                    INNER JOIN prescription_medication pm3 ON p3.prescription_id = pm3.prescription_id
                    WHERE p3.user_id = %s
                    GROUP BY p3.prescription_id
                ) as avg_calc
            )
        )
        GROUP BY p.prescription_id
        ORDER BY medicine_count DESC
        LIMIT 5
    """, (session['user_id'], session['user_id'], session['user_id']))
    complex_prescriptions = cursor.fetchall()

    return render_template('analytics.html', 
                        monthly_stats=monthly_stats,
                        medicine_stats=medicine_stats if medicine_stats else [],
                        top_issues=top_issues,
                        complex_prescriptions=complex_prescriptions)

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in!'})
    
    issue = request.form.get('issue', '').strip()
    description = request.form.get('description', '').strip()
    
    if not issue:
        return jsonify({'status': 'error', 'message': 'Please specify issue!'})
    
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file!'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected!'})
    
    if file and allowed_file(file.filename):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(file.filename)
        unique_filename = f"{session['user_id']}_{timestamp}_{filename}"
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(full_path)
        
        print("\n" + "="*60)
        print("ðŸ“¸ TRIPLE OCR EXTRACTION")
        print("="*60)
        tesseract_text, easyocr_text, google_vision_text = extract_text_triple_ocr(full_path)
        
        if not any([tesseract_text.strip(), easyocr_text.strip(), google_vision_text.strip()]):
            return jsonify({'status': 'error', 'message': 'Could not extract text!'})
        
        parsed_data = parse_prescription_with_groq_fusion(tesseract_text, easyocr_text, google_vision_text)
        
        # Date conversion
        prescription_date = None
        if parsed_data.get('date'):
            try:
                for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y']:
                    try:
                        prescription_date = datetime.strptime(parsed_data['date'], fmt).date()
                        break
                    except:
                        continue
            except:
                pass
        
        combined_text = f"TESSERACT:\n{tesseract_text}\n\nEASYOCR:\n{easyocr_text}\n\nGOOGLE:\n{google_vision_text}"
        relative_path = f"uploads/{unique_filename}"
        
        try:
            # INSERT with trigger (auto-logs to prescription_log)
            cursor.execute("""
                INSERT INTO prescription 
                (user_id, issue, description, doctor_name, prescription_date, file_path, extracted_text) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (session['user_id'], issue, description, parsed_data.get('doctor_name', ''), 
                  prescription_date, relative_path, combined_text))
            
            prescription_id = cursor.lastrowid
            
            # Save medicines (triggers medicine_count update)
            for med in parsed_data.get('medicines', []):
                cursor.execute("""
                    INSERT INTO prescription_medication 
                    (prescription_id, medicine_name, dosage, frequency, duration) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (prescription_id, med.get('name', ''), med.get('dosage', ''), 
                      med.get('frequency', ''), med.get('duration', '')))
            
            db.commit()
            print(f"ðŸ’¾ Saved prescription ID: {prescription_id}")
            
            return jsonify({
                'status': 'success', 
                'message': f'Found {len(parsed_data.get("medicines", []))} medicines!',
                'prescription_id': prescription_id
            })
        except mysql.connector.Error as err:
            print(f"âŒ Database error: {err}")
            return jsonify({'status': 'error', 'message': f'Database error: {err.msg}'})
    return jsonify({'status': 'error', 'message': 'Invalid file type!'})

@app.route('/prescription/<int:prescription_id>')
def view_prescription(prescription_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cursor.execute("""
        SELECT * FROM prescription 
        WHERE prescription_id = %s AND user_id = %s
    """, (prescription_id, session['user_id']))
    prescription = cursor.fetchone()
    
    if not prescription:
        flash('Prescription not found!', 'danger')
        return redirect(url_for('dashboard'))
    
    cursor.execute("""
        SELECT * FROM prescription_medication 
        WHERE prescription_id = %s
    """, (prescription_id,))
    medicines = cursor.fetchall()
    
    cursor.execute("SELECT GetDaysSinceLastIssue(%s, %s) as days_since_last", 
                (session['user_id'], prescription['issue']))
    days_result = cursor.fetchone()
    prescription['days_since_last_issue'] = days_result['days_since_last'] if days_result else -1

    return render_template('view_prescription.html', prescription=prescription, medicines=medicines)

@app.route('/prescription/<int:prescription_id>/edit', methods=['GET', 'POST'])
def edit_prescription(prescription_id):
    """UPDATE operation with GUI"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        issue = request.form.get('issue')
        description = request.form.get('description')
        doctor_name = request.form.get('doctor_name')
        
        cursor.execute("""
            UPDATE prescription 
            SET issue = %s, description = %s, doctor_name = %s
            WHERE prescription_id = %s AND user_id = %s
        """, (issue, description, doctor_name, prescription_id, session['user_id']))
        db.commit()
        
        flash('Prescription updated successfully!', 'success')
        return redirect(url_for('view_prescription', prescription_id=prescription_id))
    
    cursor.execute("""
        SELECT * FROM prescription 
        WHERE prescription_id = %s AND user_id = %s
    """, (prescription_id, session['user_id']))
    prescription = cursor.fetchone()
    
    return render_template('edit_prescription.html', prescription=prescription)

@app.route('/prescription/<int:prescription_id>/delete', methods=['POST'])
def delete_prescription(prescription_id):
    """DELETE operation with GUI"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in!'})
    
    try:
        # Get file path before deletion
        cursor.execute("""
            SELECT file_path FROM prescription 
            WHERE prescription_id = %s AND user_id = %s
        """, (prescription_id, session['user_id']))
        result = cursor.fetchone()
        
        if result:
            # Delete prescription (trigger will log this)
            cursor.execute("""
                DELETE FROM prescription 
                WHERE prescription_id = %s AND user_id = %s
            """, (prescription_id, session['user_id']))
            db.commit()
            
            # Delete file
            file_path = os.path.join('static', result['file_path'])
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return jsonify({'status': 'success', 'message': 'Prescription deleted!'})
        return jsonify({'status': 'error', 'message': 'Prescription not found!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/search', methods=['POST'])
def search():
    """Search using stored procedure (NESTED query with JOIN)"""
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in!'})
    
    query = request.json.get('query', '').strip()
    
    if not query:
        return jsonify({'status': 'error', 'message': 'Enter search query!'})
    
    # Call stored procedure with nested query
    cursor.callproc('SearchMedicines', [session['user_id'], query])
    
    results = []
    for result in cursor.stored_results():
        search_results = result.fetchall()
        for row in search_results:
            results.append({
                'prescription_id': row['prescription_id'],
                'issue': row['issue'],
                'doctor': row['doctor_name'] or 'Not specified',
                'date': row['prescription_date'].strftime('%d %b %Y') if row['prescription_date'] else 'Not specified',
                'medicine_name': row['medicine_name'],
                'dosage': row['dosage'],
                'frequency': row['frequency']
            })
    
    # Log query
    cursor.execute("""
        INSERT INTO ai_query_log (user_id, query_text, matched_prescription_ids, response_summary)
        VALUES (%s, %s, %s, %s)
    """, (session['user_id'], query, 
          ','.join([str(r['prescription_id']) for r in results]),
          f'Found {len(results)} results'))
    db.commit()
    
    return jsonify({
        'status': 'success',
        'query': query,
        'results': results,
        'count': len(results)
    })

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)