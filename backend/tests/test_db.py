import pytest
from run_web import create_app
from cyberhunter_3d.web.models import db, User, Scan, Target
from cyberhunter_3d.core.post_scan_operations import schedule_next_scan

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.drop_all()

def test_add_user(app):
    with app.app_context():
        user = User(username="testuser2", password_hash="test", otp_secret="test")
        db.session.add(user)
        db.session.commit()

        retrieved_user = db.session.query(User).filter_by(username="testuser2").first()
        assert retrieved_user is not None

def test_schedule_next_scan(app):
    """Tests that a new scan is scheduled correctly."""
    with app.app_context():
        # Create a user and an initial scan with a target
        user = User(username="testuser", password_hash="test", otp_secret="test")
        db.session.add(user)
        db.session.commit()

        initial_scan = Scan(user_id=user.id)
        initial_scan.targets.append(Target(value="example.com", type="domain"))
        db.session.add(initial_scan)
        db.session.commit()

        initial_scan_id = initial_scan.id

        # Run the function to schedule the next scan
        schedule_next_scan(initial_scan_id)

        # Check that a new scan has been created
        new_scans = Scan.query.filter(Scan.id != initial_scan_id).all()
        assert len(new_scans) == 1

        new_scan = new_scans[0]
        assert new_scan.status == 'PENDING'
        assert len(new_scan.targets) == 1
        assert new_scan.targets[0].value == "example.com"
