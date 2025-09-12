import pytest
import json
from unittest.mock import MagicMock
from run_web import create_app
from cyberhunter_3d.web.models import db, User, Scan, Target, Asset

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # create a temporary file to isolate the database for each test
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False # Disable CSRF for testing forms
    })

    # Attach a mock executor to the app for testing
    app.executor = MagicMock()

    yield app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture
def init_database(app):
    """Set up the database for the tests."""
    with app.app_context():
        db.create_all()
        # Create a test user
        test_user = User(username='testuser', password_hash='somehash', otp_secret='secret')
        db.session.add(test_user)
        db.session.commit()
        yield db
        db.drop_all()

def test_ping_unauthorized(client):
    """Test that ping endpoint requires an API key."""
    response = client.get('/api/v1/ping')
    assert response.status_code == 401

def test_ping_authorized(client, app, init_database):
    """Test that ping endpoint works with a valid API key."""
    with app.app_context():
        test_user = db.session.get(User, 1)
        response = client.get('/api/v1/ping', headers={'X-API-Key': test_user.api_key})
        assert response.status_code == 200
        assert json.loads(response.data)['message'] == 'pong'

def test_create_scan_api(client, app, init_database):
    """Test creating a scan via the API."""
    with app.app_context():
        test_user = db.session.get(User, 1)
        payload = {
            "targets": ["example.com", "1.1.1.1"],
            "in_scope_rules": "*.example.com"
        }
        response = client.post('/api/v1/scans',
                                    headers={'X-API-Key': test_user.api_key},
                                    data=json.dumps(payload),
                                    content_type='application/json')

        assert response.status_code == 202
        response_data = json.loads(response.data)
        assert 'scan_id' in response_data
        scan_id = response_data['scan_id']

        # Verify the scan was created in the DB
        scan = db.session.get(Scan, scan_id)
        assert scan is not None
        assert scan.user_id == test_user.id

    # Verify that the background task was called
    app.executor.submit.assert_called_once()

def test_get_scan_status_api(client, app, init_database):
    """Test getting scan status via the API."""
    with app.app_context():
        test_user = db.session.get(User, 1)
        # First, create a scan to check
        scan = Scan(user_id=test_user.id, status='COMPLETED', results='Test summary')
        db.session.add(scan)
        db.session.commit()
        scan_id = scan.id

        response = client.get(f'/api/v1/scans/{scan_id}/status', headers={'X-API-Key': test_user.api_key})
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert response_data['status'] == 'COMPLETED'
        assert response_data['summary'] == 'Test summary'

def test_get_scan_results_api(client, app, init_database):
    """Test getting scan results via the API."""
    with app.app_context():
        test_user = db.session.get(User, 1)
        # Create a scan and some assets
        scan = Scan(user_id=test_user.id, status='COMPLETED')
        db.session.add(scan)
        db.session.flush()
        asset1 = Asset(scan_id=scan.id, type='subdomain', value='test.example.com')
        asset2 = Asset(scan_id=scan.id, type='ip_address', value='1.2.3.4')
        db.session.add_all([asset1, asset2])
        db.session.commit()
        scan_id = scan.id

        response = client.get(f'/api/v1/scans/{scan_id}/results', headers={'X-API-Key': test_user.api_key})
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert len(response_data['assets']) == 2
        assert response_data['assets'][0]['value'] == 'test.example.com'

def test_get_scan_graph_api(client, app, init_database):
    """Test getting scan graph data via the API."""
    with app.app_context():
        test_user = db.session.get(User, 1)
        scan = Scan(user_id=test_user.id, status='COMPLETED')
        db.session.add(scan)
        db.session.flush()
        t1 = Target(scan_id=scan.id, type='domain', value='example.com')
        a1 = Asset(scan_id=scan.id, type='subdomain', value='test.example.com')
        db.session.add_all([t1, a1])
        db.session.commit()
        scan_id = scan.id

        response = client.get(f'/api/v1/scans/{scan_id}/graph', headers={'X-API-Key': test_user.api_key})
        assert response.status_code == 200
        response_data = json.loads(response.data)
        assert 'graph_definition' in response_data
        assert 'graph TD' in response_data['graph_definition']
        assert 'target1("example.com (domain)")' in response_data['graph_definition']
        assert 'asset1testexamplecom("test.example.com (subdomain)")' in response_data['graph_definition']
