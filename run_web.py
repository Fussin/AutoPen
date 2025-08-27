import os
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from cyberhunter_3d.web.models import db, User

# --- App Initialization ---
app = Flask(__name__, template_folder='cyberhunter_3d/web/templates', static_folder='cyberhunter_3d/web/static')

# --- Configuration ---
# In a real app, this should be a more complex, securely stored secret.
app.config['SECRET_KEY'] = 'a-very-secret-key-that-should-be-changed'
# Define the database path
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cyberhunter.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Extensions Initialization ---
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # The route to redirect to for login

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login hook to load a user by ID."""
    return User.query.get(int(user_id))

# --- Database Initialization ---
def init_database():
    """Create database tables if they don't exist."""
    if not os.path.exists(db_path):
        with app.app_context():
            print("Creating database and tables...")
            db.create_all()
            print("Database initialized.")
    else:
        print("Database already exists.")

# --- Routes ---
from cyberhunter_3d.web.api import api_bp
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_user, current_user, login_required
import pyotp
import qrcode
import io
import base64

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        # Create new user
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        otp_secret = pyotp.random_base32()

        new_user = User(username=username, password_hash=password_hash, otp_secret=otp_secret)
        db.session.add(new_user)
        db.session.commit()

        # Log in the new user to proceed to 2FA setup
        login_user(new_user)

        flash('Account created successfully! Please set up 2FA.', 'success')
        return redirect(url_for('setup_2fa'))

    return render_template('register.html')

@app.route('/setup-2fa')
@login_required
def setup_2fa():
    # Generate TOTP provisioning URI
    totp = pyotp.TOTP(current_user.otp_secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.username,
        issuer_name="CyberHunter 3D"
    )

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    # Save QR code to a bytes buffer and encode it in base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_code_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return render_template('setup_2fa.html', qr_code_data=qr_code_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            # Password is correct, now prompt for 2FA.
            # Store user_id in session to know who is trying to verify.
            session['user_id_for_2fa'] = user.id
            return redirect(url_for('verify_2fa'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/verify-2fa', methods=['GET', 'POST'])
def verify_2fa():
    if 'user_id_for_2fa' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        user_id = session['user_id_for_2fa']
        user = User.query.get(user_id)
        token = request.form.get('token')

        totp = pyotp.TOTP(user.otp_secret)
        if totp.verify(token):
            # 2FA is correct, log user in.
            login_user(user)
            session.pop('user_id_for_2fa', None) # Clean up session
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid 2FA token.', 'danger')
            return redirect(url_for('verify_2fa'))

    return render_template('verify_2fa.html')

from flask_login import logout_user

from cyberhunter_3d.web.models import Scan, Target
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor
from cyberhunter_3d.core.scan_manager import run_discovery_phase

# --- Background Task Executor ---
# Using a simple thread pool for background tasks.
# For a production app, a more robust solution like Celery would be better.
executor = ThreadPoolExecutor(max_workers=2)

# Register the API blueprint
app.register_blueprint(api_bp)

@app.route('/submit-targets', methods=['POST'])
@login_required
def submit_targets():
    targets_text = request.form.get('targets', '')
    target_file = request.files.get('target_file')

    raw_targets = []

    # 1. Get targets from textarea
    if targets_text:
        raw_targets.extend(targets_text.strip().splitlines())

    # 2. Get targets from file
    if target_file and target_file.filename != '':
        # It's good practice to secure the filename, though we don't save the file
        filename = secure_filename(target_file.filename)
        if filename.endswith('.txt') or filename.endswith('.csv'):
            try:
                content = target_file.read().decode('utf-8')
                raw_targets.extend(content.strip().splitlines())
            except Exception as e:
                flash(f"Error reading file: {e}", 'danger')
                return redirect(url_for('dashboard'))

    # 3. Clean and validate targets
    targets = {line.strip() for line in raw_targets if line.strip()}

    if not targets:
        flash('No valid targets submitted.', 'danger')
        return redirect(url_for('dashboard'))

    # 4. Create Scan and Target objects in DB
    new_scan = Scan(user_id=current_user.id, status='QUEUED')
    db.session.add(new_scan)

    # We need to flush to get the new_scan.id before creating targets
    db.session.flush()

    for target_value in targets:
        new_target = Target(value=target_value, scan_id=new_scan.id)
        db.session.add(new_target)

    db.session.commit()

    # Trigger the scan in the background
    executor.submit(run_discovery_phase, new_scan.id, app)

    flash(f'{len(targets)} targets have been queued for scanning.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
@login_required
def dashboard():
    # Fetch scans for the current user, ordered by most recent
    scans = Scan.query.filter_by(user_id=current_user.id).order_by(Scan.created_at.desc()).all()
    return render_template('dashboard.html', scans=scans)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/scan/<int:scan_id>')
@login_required
def scan_results(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    # Ensure the user can only view their own scans
    if scan.user_id != current_user.id:
        flash('You are not authorized to view this scan.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('scan_results.html', scan=scan)

# --- Main Execution ---
if __name__ == '__main__':
    init_database()
    # In a real deployment, use a proper WSGI server like Gunicorn.
    app.run(debug=True, port=5001)
