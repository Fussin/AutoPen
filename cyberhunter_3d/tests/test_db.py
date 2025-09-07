import pytest
from run_web import app as main_app, db as main_db
from cyberhunter_3d.web.models import User, Scan, Target
from cyberhunter_3d.core.post_scan_operations import schedule_next_scan

@pytest.fixture
def test_app():
    """Uses the main Flask app for testing with an in-memory SQLite database."""
    main_app.config['TESTING'] = True
    main_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    main_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with main_app.app_context():
        main_db.create_all()

    yield main_app

    with main_app.app_context():
        main_db.drop_all()

def test_add_user(test_app):
    with test_app.app_context():
        user = User(username="testuser2", password_hash="test", otp_secret="test")
        main_db.session.add(user)
        main_db.session.commit()

        retrieved_user = main_db.session.query(User).filter_by(username="testuser2").first()
        assert retrieved_user is not None

def test_schedule_next_scan(test_app):
    """Tests that a new scan is scheduled correctly."""
    with test_app.app_context():
        # Create a user and an initial scan with a target
        user = User(username="testuser", password_hash="test", otp_secret="test")
        main_db.session.add(user)
        main_db.session.commit()

        initial_scan = Scan(user_id=user.id)
        initial_scan.targets.append(Target(value="example.com", type="domain"))
        main_db.session.add(initial_scan)
        main_db.session.commit()

        initial_scan_id = initial_scan.id

        # Run the function to schedule the next scan
        schedule_next_scan(initial_scan)

        # Check that a new scan has been created
        new_scans = Scan.query.filter(Scan.id != initial_scan_id).all()
        assert len(new_scans) == 1

        new_scan = new_scans[0]
        assert new_scan.status == 'PENDING'
        assert len(new_scan.targets) == 1
        assert new_scan.targets[0].value == "example.com"
