import os

class Config:
    # --- General Config ---
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-very-secret-key-that-should-be-changed')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Database Config ---
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cyberhunter.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{DB_PATH}')

    # --- Mail Server Config ---
    # For testing, you can use a dummy server or a service like Mailtrap.
    # For production, use a real SMTP server (e.g., SendGrid, Mailgun, or your own).
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.mailtrap.io')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 2525))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'your-mailtrap-username')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'your-mailtrap-password')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@cyberhunter3d.com')
