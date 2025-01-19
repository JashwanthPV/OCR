from flask import Flask, render_template, request, jsonify, send_file
import os
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
import base64
from io import BytesIO
from fpdf import FPDF
from docx import Document
import pandas as pd
from PyPDF2 import PdfReader  # Added for PDF text extraction

# Ensure Tesseract executable is in your PATH or specify its location
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'xls', 'xlsx', 'docx'}

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to preprocess image for better OCR accuracy
def preprocess_image(image):
    # Convert to grayscale
    image = image.convert('L')
    # Apply thresholding to get a binary image (helps with better recognition)
    image = image.point(lambda p: p > 128 and 255)
    # Optionally apply blur or sharpen for better readability
    return image

# Function to process a single document using Tesseract OCR
def process_document(image, lang='eng'):
    # Preprocess the image before passing to Tesseract
    image = preprocess_image(image)
    
    # Use Tesseract to extract text from the image
    text = pytesseract.image_to_string(image, config=f'--oem 1 --psm 3')  # example for English

    
    return text

# Function to create PDF from extracted text
def text_to_pdf(text, filename='result.pdf'):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.multi_cell(0, 10, text)
    pdf.output(filename)
    return filename

# Function to extract text from DOCX
def extract_text_from_docx(file_path):
    doc = Document(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# Function to extract text from Excel (XLS, XLSX)
def extract_text_from_excel(file_path):
    df = pd.read_excel(file_path, None)  # Read all sheets
    text = ""
    for sheet in df.values():
        text += sheet.to_string() + "\n"
    return text

# Function to extract text from PDF
def extract_text_from_pdf(file_path):
    text = ''
    with open(file_path, 'rb') as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text += page.extract_text()
    return text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'document' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['document']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'File type not supported'}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Process file based on its type
    file_extension = filename.rsplit('.', 1)[1].lower()

    if file_extension in {'jpg', 'jpeg', 'png'}:
        # Image file - Process with OCR
        image = Image.open(file_path)
        text = process_document(image)
    elif file_extension == 'pdf':
        # PDF file - Extract text from PDF
        text = extract_text_from_pdf(file_path)
    elif file_extension in {'xls', 'xlsx'}:
        # Excel file - Extract text from Excel
        text = extract_text_from_excel(file_path)
    elif file_extension == 'docx':
        # DOCX file - Extract text from DOCX
        text = extract_text_from_docx(file_path)

    return render_template('result.html', text=text)

@app.route('/upload_camera', methods=['POST'])
def upload_camera_image():
    data = request.get_json()
    image_data = data['image']

    # Decode the base64 image
    image_data = image_data.split(",")[1]  # Remove the prefix data:image/png;base64,
    img_bytes = base64.b64decode(image_data)
    image = Image.open(BytesIO(img_bytes))

    # Process image with Tesseract OCR
    text = process_document(image)

    return jsonify({'text': text})

@app.route('/download_txt', methods=['POST'])
def download_txt():
    text = request.form['text']
    filename = 'extracted_text.txt'
    with open(filename, 'w') as file:
        file.write(text)
    return send_file(filename, as_attachment=True)

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    text = request.form['text']
    pdf_filename = text_to_pdf(text)
    return send_file(pdf_filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
