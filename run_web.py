import os
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from config import Config
from cyberhunter_3d.web.models import db, User

# --- App Initialization ---
app = Flask(__name__, template_folder='cyberhunter_3d/web/templates', static_folder='cyberhunter_3d/web/static')
app.config.from_object(Config)

from cyberhunter_3d.core.reporting.email_service import mail

# --- Extensions Initialization ---
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
mail.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Database Initialization ---
def init_database():
    if not os.path.exists(app.config['DB_PATH']):
        with app.app_context():
            print("Creating database and tables...")
            db.create_all()
            print("Database initialized.")
    else:
        print("Database already exists.")

# --- Routes ---
from cyberhunter_3d.web.api import api_bp
from flask import render_template, request, redirect, url_for, flash, session
from flask_login import login_user, current_user, login_required, logout_user
import pyotp
import qrcode
import io
import base64
from cyberhunter_3d.web.models import Scan, Target, Vulnerability
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor
from cyberhunter_3d.core.scan_manager import run_discovery_phase
from cyberhunter_3d.core.target_parser import parse_single_target
from apscheduler.schedulers.background import BackgroundScheduler
from cyberhunter_3d.core.feeds.feed_manager import check_for_new_targets

# --- Background Task Executor ---
executor = ThreadPoolExecutor(max_workers=2)

# --- Scheduler Setup ---
# Initialized in the global scope to ensure it's started when run
# with a production WSGI server like Gunicorn.
scheduler = BackgroundScheduler()
# Run the job every 4 hours
scheduler.add_job(check_for_new_targets, 'interval', hours=4, args=[app])
scheduler.start()
print("Scheduler started successfully.")

# Register the API blueprint
app.register_blueprint(api_bp)

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
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        otp_secret = pyotp.random_base32()
        new_user = User(username=username, password_hash=password_hash, otp_secret=otp_secret)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash('Account created successfully! Please set up 2FA.', 'success')
        return redirect(url_for('setup_2fa'))
    return render_template('register.html')

@app.route('/setup-2fa')
@login_required
def setup_2fa():
    totp = pyotp.TOTP(current_user.otp_secret)
    provisioning_uri = totp.provisioning_uri(name=current_user.username, issuer_name="CyberHunter 3D")
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
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

    user_id = session['user_id_for_2fa']
    user = db.session.get(User, user_id)

    if not user:
        flash('User not found, please log in again.', 'danger')
        session.pop('user_id_for_2fa', None)
        return redirect(url_for('login'))

    if request.method == 'POST':
        token = request.form.get('token')
        totp = pyotp.TOTP(user.otp_secret)

        if totp.verify(token):
            login_user(user)
            session.pop('user_id_for_2fa', None)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid 2FA token.', 'danger')
            return redirect(url_for('verify_2fa'))

    return render_template('verify_2fa.html')

@app.route('/submit-targets', methods=['POST'])
@login_required
def submit_targets():
    targets_text = request.form.get('targets', '')
    target_file = request.files.get('target_file')
    raw_targets = []
    if targets_text:
        raw_targets.extend(targets_text.strip().splitlines())
    if target_file and target_file.filename != '':
        filename = secure_filename(target_file.filename)
        if filename.endswith(('.txt', '.csv')):
            try:
                content = target_file.read().decode('utf-8')
                raw_targets.extend(content.strip().splitlines())
            except Exception as e:
                flash(f"Error reading file: {e}", 'danger')
                return redirect(url_for('dashboard'))
    parsed_targets = []
    invalid_targets = []
    for raw_target in raw_targets:
        if not raw_target.strip():
            continue
        value, type = parse_single_target(raw_target)
        if type not in ['unknown', 'empty']:
            parsed_targets.append({'value': value, 'type': type})
        else:
            invalid_targets.append(raw_target)
    if not parsed_targets:
        flash('No valid targets were submitted.', 'danger')
        if invalid_targets:
            flash(f"The following {len(invalid_targets)} targets were invalid: {', '.join(invalid_targets)}", 'warning')
        return redirect(url_for('dashboard'))
    new_scan = Scan(user_id=current_user.id, status='QUEUED')
    db.session.add(new_scan)
    db.session.flush()
    for p_target in parsed_targets:
        new_target = Target(value=p_target['value'], type=p_target['type'], scan_id=new_scan.id)
        db.session.add(new_target)
    db.session.commit()
    executor.submit(run_discovery_phase, new_scan.id, app)
    flash(f'{len(parsed_targets)} targets have been queued for scanning.', 'success')
    if invalid_targets:
        flash(f"The following {len(invalid_targets)} targets were invalid and have been ignored: {', '.join(invalid_targets)}", 'warning')
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    scans = Scan.query.filter_by(user_id=current_user.id).order_by(Scan.created_at.desc()).all()
    return render_template('dashboard.html', scans=scans)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        form_name = request.form.get('form_name')

        if form_name == 'api_key':
            current_user.regenerate_api_key()
            db.session.commit()
            flash('API key has been regenerated.', 'success')

        elif form_name == 'h1_key':
            h1_username = request.form.get('h1_username')
            h1_key = request.form.get('h1_key')
            current_user.hackerone_username = h1_username
            current_user.hackerone_api_key = h1_key
            db.session.commit()
            flash('HackerOne credentials updated.', 'success')

        elif form_name == 'autonomous_scanning':
            is_enabled = 'autonomous_enabled' in request.form
            current_user.is_autonomous_scanning_enabled = is_enabled
            db.session.commit()
            flash(f"Autonomous scanning has been {'enabled' if is_enabled else 'disabled'}.", 'success')

        elif form_name == 'email_notifications':
            email = request.form.get('email')
            is_enabled = 'email_enabled' in request.form
            current_user.email = email
            current_user.is_email_notifications_enabled = is_enabled
            db.session.commit()
            flash('Email notification settings updated.', 'success')

        return redirect(url_for('profile'))

    return render_template('profile.html')

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
    if scan.user_id != current_user.id:
        flash('You are not authorized to view this scan.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('scan_results.html', scan=scan)

@app.route('/scan/<int:scan_id>/graph_view')
@login_required
def graph_view(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    if scan.user_id != current_user.id:
        flash('You are not authorized to view this scan.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('graph_view.html', scan=scan)

@app.route('/vulnerability/<int:vuln_id>')
@login_required
def vulnerability_details(vuln_id):
    vuln = Vulnerability.query.get_or_404(vuln_id)
    # Ensure the current user is authorized to see this vulnerability
    if vuln.scan_ref.user_id != current_user.id:
        flash('You are not authorized to view this vulnerability.', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('vulnerability_details.html', vuln=vuln)

# --- Main Execution ---
if __name__ == '__main__':
    init_database()
    # The scheduler is started in the global scope, so we don't need to start it here.
    # use_reloader=False is important to prevent the scheduler from running twice.
    app.run(debug=True, port=5001, use_reloader=False)
