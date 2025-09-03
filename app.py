import os
import uuid
import json
import qrcode
import logging
import threading
import time
from datetime import datetime
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import pdfkit
import shutil

logging.basicConfig(level=logging.DEBUG)

def get_wkhtmltopdf_path():
    """
    Automatically detect wkhtmltopdf path for cross-platform compatibility
    """
    # Try common paths in order of preference
    possible_paths = [
        # Replit Nix path
        '/nix/store/hxiay4lkq4389vxnhnb3d0pbaw6siwkw-wkhtmltopdf/bin/wkhtmltopdf',
        # System PATH (most common)
        shutil.which('wkhtmltopdf'),
        # Common Linux paths
        '/usr/bin/wkhtmltopdf',
        '/usr/local/bin/wkhtmltopdf',
        # PythonAnywhere paths
        '/usr/local/bin/wkhtmltopdf',
        '/home/username/.local/bin/wkhtmltopdf',
        # Ubuntu/Debian
        '/usr/bin/wkhtmltopdf',
        # Windows paths
        'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
        'C:\\Program Files (x86)\\wkhtmltopdf\\bin\\wkhtmltopdf.exe',
        # macOS paths
        '/usr/local/bin/wkhtmltopdf',
        '/opt/homebrew/bin/wkhtmltopdf'
    ]
    
    for path in possible_paths:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            logging.info(f"Found wkhtmltopdf at: {path}")
            return path
    
    # If no path found, return None to use system default
    logging.warning("wkhtmltopdf not found in common paths, using system default")
    return None

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Custom template filter for currency formatting
@app.template_filter('currency')
def currency_filter(value):
    """Format currency with thousands separator"""
    try:
        return "{:,.2f}".format(float(value))
    except (ValueError, TypeError):
        return "0.00"

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

def delete_file_after_delay(file_path, delay_seconds=60):
    """Delete a file after a specified delay"""
    def delete_file():
        try:
            time.sleep(delay_seconds)
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Deleted file: {file_path}")
        except Exception as e:
            logging.error(f"Error deleting file {file_path}: {e}")
    
    # Run deletion in a separate thread
    thread = threading.Thread(target=delete_file, daemon=True)
    thread.start()

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
        
        # Ensure items is a proper list and calculate totals
        items_data = data.get('items', [])
        if not isinstance(items_data, list):
            data['items'] = []
        else:
            data['items'] = items_data
        
        # Calculate subtotal, tax, and grand total if not provided
        if 'subtotal' not in data or 'tax_amount' not in data or 'grand_total' not in data:
            subtotal = sum(float(item.get('quantity', 0)) * float(item.get('price', 0)) for item in data['items'])
            tax_rate = float(data.get('tax_rate', 0))
            discount = float(data.get('discount', 0))
            tax_amount = (subtotal * tax_rate) / 100
            grand_total = subtotal + tax_amount - discount
            
            data['subtotal'] = "{:.2f}".format(subtotal)
            data['tax_amount'] = "{:.2f}".format(tax_amount)
            data['grand_total'] = "{:.2f}".format(max(0, grand_total))
        
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
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img.save(qr_path)
        
        # Add QR code path to data
        data['qr_code_path'] = os.path.abspath(qr_path)
        
        # Convert logo filename to absolute path for PDF generation
        if data.get('logo_filename'):
            logo_path = os.path.join(app.config['UPLOAD_FOLDER'], data['logo_filename'])
            data['logo_absolute_path'] = os.path.abspath(logo_path)
        
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
        
        # Configure wkhtmltopdf path automatically
        wkhtmltopdf_path = get_wkhtmltopdf_path()
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path) if wkhtmltopdf_path else None
        
        # Generate PDF
        pdf_filename = f"receipt_{data.get('receipt_id')}.pdf"
        pdf_path = os.path.join('static', pdf_filename)
        
        try:
            if config:
                pdfkit.from_string(html_content, pdf_path, options=options, configuration=config)
            else:
                # Try without configuration (system default)
                pdfkit.from_string(html_content, pdf_path, options=options)
        except OSError as e:
            if "wkhtmltopdf" in str(e).lower():
                error_msg = "PDF generation requires wkhtmltopdf to be installed. Please install it using: sudo apt-get install wkhtmltopdf (Ubuntu/Debian) or visit https://wkhtmltopdf.org/downloads.html for other platforms."
                logging.error(f"wkhtmltopdf not found: {e}")
                return jsonify({'error': error_msg}), 500
            else:
                raise
        
        # Schedule automatic deletion of generated files after 1 minute
        delete_file_after_delay(pdf_path, 60)
        delete_file_after_delay(qr_path, 60)
        
        return jsonify({
            'success': True,
            'receipt_id': data.get('receipt_id'),
            'pdf_filename': pdf_filename,
            'qr_url': data['qr_code_path']
        })
        
    except Exception as e:
        logging.error(f"Error generating receipt: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_pdf/<filename>')
def download_pdf(filename):
    try:
        # Validate filename to prevent directory traversal
        if not filename or '..' in filename or '/' in filename:
            return jsonify({'error': 'Invalid filename'}), 400
            
        pdf_path = os.path.join('static', filename)
        
        # Check if file exists
        if not os.path.exists(pdf_path):
            return jsonify({'error': 'File not found'}), 404
            
        return send_file(pdf_path, as_attachment=True, download_name=filename)
    except Exception as e:
        logging.error(f"Error downloading PDF: {e}")
        return jsonify({'error': 'Error downloading PDF file'}), 500

@app.route('/download_receipt/<receipt_id>')
def download_receipt(receipt_id):
    try:
        # Validate receipt_id to prevent directory traversal
        if not receipt_id or '..' in receipt_id or '/' in receipt_id:
            return jsonify({'error': 'Invalid receipt ID'}), 400
            
        pdf_filename = f"receipt_{receipt_id}.pdf"
        pdf_path = os.path.join('static', pdf_filename)
        
        if os.path.exists(pdf_path):
            return send_file(pdf_path, as_attachment=True, download_name=pdf_filename)
        else:
            return jsonify({'error': 'Receipt file not found'}), 404
    except Exception as e:
        logging.error(f"Error downloading receipt: {e}")
        return jsonify({'error': 'Error downloading receipt file'}), 500

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
