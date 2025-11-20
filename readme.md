# MediVault 💊

**Your Digital Prescription Vault for Safe and Smart Healthcare**

MediVault is a web-based prescription management system that uses AI-powered OCR to digitize, store, and intelligently retrieve medical prescriptions. Never lose a prescription again!

---

## ✨ Features

- 🔐 **Secure User Authentication** - Password hashing with bcrypt
- 📸 **Triple OCR Technology** - Tesseract + EasyOCR + Google Vision API
- 🤖 **AI-Powered Extraction** - Groq AI (Llama 3.3) intelligently parses prescription data
- 🔍 **Smart Search** - Find prescriptions by medicine, issue, or doctor name
- 📊 **Medical Analytics** - Track prescription trends and medicine usage
- ✏️ **Full CRUD Operations** - Create, read, update, and delete prescriptions with GUI
- 🗄️ **Advanced Database** - MySQL with triggers, stored procedures, and aggregate queries

---

## 🛠️ Tech Stack

**Backend:** Python, Flask, MySQL  
**Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript  
**OCR:** Tesseract, EasyOCR, Google Vision API  
**AI:** Groq API (Llama 3.3 70B)

---

## 📦 Installation

### Prerequisites
- Python 3.8+
- MySQL 8.0+
- Tesseract OCR
- Google Cloud Vision API credentials

### Setup Steps

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/medivault.git
cd medivault
```

2. **Install dependencies**
```bash
pip install flask mysql-connector-python pytesseract pillow easyocr google-cloud-vision requests werkzeug
```

3. **Configure Tesseract path** (Windows)
```python
# In app.py, update line:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

4. **Setup MySQL Database**
```bash
mysql -u root -p < medivault.sql
```

5. **Configure environment variables**
```bash
# Update in app.py:
- MySQL credentials (host, user, password)
- Groq API key
- Google Vision API key path
```

6. **Run the application**
```bash
python app.py
```

7. **Open browser**
```
http://localhost:5000
```

---

## 📁 Project Structure

```
MediVault/
│
├── app.py                          # Flask application
├── medivault.sql                   # Database schema
├── google-vision-key.json          # Google API credentials
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── script.js
│   ├── img/
│   └── uploads/                    # Prescription images
│
└── templates/
    ├── base.html
    ├── index.html
    ├── login.html
    ├── signup.html
    ├── dashboard.html
    ├── view_prescription.html
    ├── edit_prescription.html
    └── analytics.html
```

---

## 🗃️ Database Schema

**Entities:** User, Prescription, Prescription_Medication, Prescription_Log

**Key Features:**
- 3NF Normalization
- Foreign key constraints with CASCADE deletion
- Triggers for auto-logging and medicine count updates
- Stored procedures for complex queries
- Indexed columns for optimized search

---

## 🚀 Usage

1. **Sign Up** - Create your account
2. **Upload** - Take a photo of your prescription and upload
3. **AI Extracts** - System automatically extracts medicines, dosage, and doctor info
4. **Search** - Find past prescriptions by medicine name or health issue
5. **Analyze** - View trends and statistics on your medical history

