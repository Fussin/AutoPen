from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# This db object will be initialized in our main application file (run_web.py)
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    User model for authentication and storing user data.
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # Field to store the secret key for TOTP (Time-based One-Time Password)
    otp_secret = db.Column(db.String(16), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'
