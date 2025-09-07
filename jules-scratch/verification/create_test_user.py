import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from run_web import app, db, bcrypt
from cyberhunter_3d.web.models import User

with app.app_context():
    # Check if user exists
    if User.query.filter_by(username='test').first():
        print("User 'test' already exists.")
    else:
        # Create a test user
        username = 'test'
        password = 'password'
        otp_secret = "FWPQ7CKOCOA7P4S7IS3CXONMB756FAED" # Same as in setup_auth.py
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password_hash=password_hash, otp_secret=otp_secret)
        db.session.add(new_user)
        db.session.commit()
        print("User 'test' created successfully.")
