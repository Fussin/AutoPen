import pytest
from run_web import app, db, bcrypt
from cyberhunter_3d.web.models import User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for testing forms
    client = app.test_client()

    with app.app_context():
        db.create_all()
        # Create a test user
        password_hash = bcrypt.generate_password_hash('password').decode('utf-8')
        user = User(username='testuser', password_hash=password_hash, otp_secret='JBSWY3DPEHPK3PXP')
        db.session.add(user)
        db.session.commit()

    yield client

    with app.app_context():
        db.drop_all()
