# --- Certificate Generator Backend ---
# 1. Save this code as `app.py`.
# 2. Create a folder named `templates` and place `certificate_generator.html` inside it.
# 3. Install required packages:
#    pip install Flask Flask-SQLAlchemy Flask-Cors gunicorn
# 4. Run the server from your terminal:
#    gunicorn app:app
# 5. Open your browser and go to http://127.0.0.1:8000

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

# --- App Configuration ---
# Flask will automatically look for the 'templates' folder.
app = Flask(__name__)
CORS(app) # Enable Cross-Origin Resource Sharing for all routes

# --- Database Configuration ---
# This sets up a simple SQLite database file.
# On Render, this will be created in the persistent disk directory.
data_dir = os.environ.get('RENDER_DATA_DIR', os.path.abspath(os.path.dirname(__file__)))
db_path = os.path.join(data_dir, 'certificates.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Database Model ---
# This defines the structure of the 'certificates' table in the database.
class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    # Using Text type to store the base64 image data, which can be long.
    image_data = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Certificate {self.name} - {self.code}>'

# --- HTML Serving Route ---
@app.route('/')
def serve_index():
    """
    Serves the main HTML file of the application using render_template.
    """
    return render_template('certificate_generator.html')


# --- API Routes ---

@app.route('/api/certificates', methods=['POST'])
def add_certificate():
    """
    API endpoint to add a single new certificate to the database.
    Expects a JSON payload with 'name', 'code', and 'image_data'.
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['name', 'code', 'image_data']):
        return jsonify({'error': 'Missing data'}), 400

    # Check if code already exists
    if Certificate.query.filter_by(code=data['code']).first():
        return jsonify({'error': 'Certificate code already exists'}), 409

    new_cert = Certificate(
        name=data['name'],
        code=data['code'],
        image_data=data['image_data']
    )
    db.session.add(new_cert)
    db.session.commit()

    return jsonify({'message': 'Certificate created successfully', 'id': new_cert.id}), 201

@app.route('/api/certificates/bulk', methods=['POST'])
def add_bulk_certificates():
    """
    API endpoint to add multiple certificates in one go.
    Expects a JSON payload like: { "certificates": [ { "name": ..., "code": ..., "image_data": ... }, ... ] }
    """
    data = request.get_json()
    if not data or 'certificates' not in data:
        return jsonify({'error': 'Missing certificate list'}), 400

    certs_to_add = []
    for cert_data in data['certificates']:
        if not all(k in cert_data for k in ['name', 'code', 'image_data']):
            continue # Skip malformed entries
        
        # Simple check for duplicates within the batch and DB
        if not Certificate.query.filter_by(code=cert_data['code']).first():
            new_cert = Certificate(
                name=cert_data['name'],
                code=cert_data['code'],
                image_data=cert_data['image_data']
            )
            certs_to_add.append(new_cert)

    if not certs_to_add:
        return jsonify({'message': 'No new certificates to add or data was invalid.'}), 200

    db.session.bulk_save_objects(certs_to_add)
    db.session.commit()

    return jsonify({'message': f'Successfully added {len(certs_to_add)} certificates.'}), 201


@app.route('/api/certificates/<string:code>', methods=['GET'])
def get_certificate(code):
    """
    API endpoint to retrieve a certificate by its unique code.
    Returns the certificate data if found, otherwise returns a 404 error.
    """
    cert = Certificate.query.filter_by(code=code).first()
    if cert:
        return jsonify({
            'name': cert.name,
            'code': cert.code,
            'image_data': cert.image_data
        })
    else:
        return jsonify({'error': 'Certificate not found'}), 404

# --- Main Execution ---
# This part is for local development and won't be used by Gunicorn on Render.
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)
