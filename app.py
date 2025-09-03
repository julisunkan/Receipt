import os
import uuid
import json
import qrcode
import logging
from datetime import datetime
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import pdfkit

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure upload settings
UPLOAD_FOLDER = 'static/uploads'
QR_FOLDER = 'static/qr'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['QR_FOLDER'] = QR_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_receipt_id():
    """Generate a unique receipt ID"""
    return f"RCP-{str(uuid.uuid4())[:8].upper()}"

def load_currencies():
    """Load currency data from JSON file"""
    try:
        with open('static/currencies.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading currencies: {e}")
        return [{"code": "USD", "symbol": "$", "name": "US Dollar"}]

@app.route('/')
def index():
    currencies = load_currencies()
    return render_template('index.html', currencies=currencies, receipt_id=generate_receipt_id())

@app.route('/upload_logo', methods=['POST'])
def upload_logo():
    if 'logo' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['logo']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to prevent overwrites
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(datetime.now().timestamp())}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'filename': filename, 'url': f'/static/uploads/{filename}'})
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/generate_receipt', methods=['POST'])
def generate_receipt():
    try:
        # Get form data
        data = request.get_json()
        
        # Generate QR code with receipt summary
        qr_data = {
            'receipt_id': data.get('receipt_id'),
            'business_name': data.get('business_name'),
            'client_name': data.get('client_name'),
            'total': data.get('grand_total'),
            'date': data.get('date'),
            'status': data.get('payment_status')
        }
        
        qr_filename = f"qr_{data.get('receipt_id')}.png"
        qr_path = os.path.join(app.config['QR_FOLDER'], qr_filename)
        
        qr = qrcode.main.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img.save(qr_path)
        
        # Add QR code path to data
        data['qr_code_path'] = f'/static/qr/{qr_filename}'
        
        # Generate PDF
        html_content = render_template('receipt_pdf.html', data=data)
        
        # PDF options
        options = {
            'page-size': 'A4',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': "UTF-8",
            'no-outline': None,
            'enable-local-file-access': None
        }
        
        # Generate PDF
        pdf_filename = f"receipt_{data.get('receipt_id')}.pdf"
        pdf_path = os.path.join('static', pdf_filename)
        
        pdfkit.from_string(html_content, pdf_path, options=options)
        
        return jsonify({
            'success': True,
            'pdf_url': f'/download_pdf/{pdf_filename}',
            'qr_url': data['qr_code_path']
        })
        
    except Exception as e:
        logging.error(f"Error generating receipt: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_pdf/<filename>')
def download_pdf(filename):
    try:
        pdf_path = os.path.join('static', filename)
        return send_file(pdf_path, as_attachment=True, download_name=filename)
    except Exception as e:
        logging.error(f"Error downloading PDF: {e}")
        flash('Error downloading PDF file', 'error')
        return redirect(url_for('index'))

@app.route('/export_business_settings', methods=['POST'])
def export_business_settings():
    try:
        data = request.get_json()
        business_data = {
            'business_name': data.get('business_name', ''),
            'business_address': data.get('business_address', ''),
            'business_email': data.get('business_email', ''),
            'business_phone': data.get('business_phone', ''),
            'logo_filename': data.get('logo_filename', '')
        }
        
        # Create JSON file
        json_content = json.dumps(business_data, indent=2)
        json_buffer = BytesIO(json_content.encode('utf-8'))
        json_buffer.seek(0)
        
        return send_file(
            json_buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name='business_settings.json'
        )
        
    except Exception as e:
        logging.error(f"Error exporting business settings: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
