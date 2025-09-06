import pytest
import json
from unittest.mock import MagicMock
from run_web import app as main_app, db as main_db
from cyberhunter_3d.web.models import User, Scan, Target, Asset

@pytest.fixture
def client_with_user():
    """A pytest fixture to set up the test client, database, and a test user."""
    main_app.config['TESTING'] = True
    main_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Attach a mock executor to the app for testing
    mock_executor = MagicMock()
    main_app.executor = mock_executor

    with main_app.test_client() as client:
        with main_app.app_context():
            main_db.create_all()
            # Create a test user
            test_user = User(username='testuser', password_hash='somehash', otp_secret='secret')
            main_db.session.add(test_user)
            main_db.session.commit()
            user_id = test_user.id
        yield client, user_id, mock_executor

    with main_app.app_context():
        main_db.drop_all()

def test_ping_unauthorized(client_with_user):
    """Test that ping endpoint requires an API key."""
    test_client, _, _ = client_with_user
    response = test_client.get('/api/v1/ping')
    assert response.status_code == 401

def test_ping_authorized(client_with_user):
    """Test that ping endpoint works with a valid API key."""
    test_client, user_id, _ = client_with_user
    with main_app.app_context():
        test_user = main_db.session.get(User, user_id)
        response = test_client.get('/api/v1/ping', headers={'X-API-Key': test_user.api_key})
        assert response.status_code == 200
        assert json.loads(response.data)['message'] == 'pong'

def test_create_scan_api(client_with_user):
    """Test creating a scan via the API."""
    test_client, user_id, mock_executor = client_with_user

    with main_app.app_context():
        test_user = main_db.session.get(User, user_id)
        payload = {
            "targets": ["example.com", "1.1.1.1"],
            "in_scope_rules": "*.example.com"
        }
        response = test_client.post('/api/v1/scans',
                                    headers={'X-API-Key': test_user.api_key},
                                    data=json.dumps(payload),
                                    content_type='application/json')

    assert response.status_code == 202
    response_data = json.loads(response.data)
    assert 'scan_id' in response_data
    scan_id = response_data['scan_id']

    # Verify the scan was created in the DB within an app context
    with main_app.app_context():
        scan = main_db.session.get(Scan, scan_id)
        assert scan is not None
        assert scan.user_id == user_id

    # Verify that the background task was called
    mock_executor.submit.assert_called_once()

def test_get_scan_status_api(client_with_user):
    """Test getting scan status via the API."""
    test_client, user_id, _ = client_with_user
    with main_app.app_context():
        test_user = main_db.session.get(User, user_id)
        # First, create a scan to check
        scan = Scan(user_id=user_id, status='COMPLETED', results='Test summary')
        main_db.session.add(scan)
        main_db.session.commit()
        scan_id = scan.id

        response = test_client.get(f'/api/v1/scans/{scan_id}/status', headers={'X-API-Key': test_user.api_key})
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['status'] == 'COMPLETED'
    assert response_data['summary'] == 'Test summary'

def test_get_scan_results_api(client_with_user):
    """Test getting scan results via the API."""
    test_client, user_id, _ = client_with_user
    with main_app.app_context():
        test_user = main_db.session.get(User, user_id)
        # Create a scan and some assets
        scan = Scan(user_id=user_id, status='COMPLETED')
        main_db.session.add(scan)
        main_db.session.flush()
        asset1 = Asset(scan_id=scan.id, type='subdomain', value='test.example.com')
        asset2 = Asset(scan_id=scan.id, type='ip_address', value='1.2.3.4')
        main_db.session.add_all([asset1, asset2])
        main_db.session.commit()
        scan_id = scan.id

        response = test_client.get(f'/api/v1/scans/{scan_id}/results', headers={'X-API-Key': test_user.api_key})
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert len(response_data['assets']) == 2
    assert response_data['assets'][0]['value'] == 'test.example.com'

def test_get_scan_graph_api(client_with_user):
    """Test getting scan graph data via the API."""
    test_client, user_id, _ = client_with_user
    with main_app.app_context():
        test_user = main_db.session.get(User, user_id)
        scan = Scan(user_id=user_id, status='COMPLETED')
        main_db.session.add(scan)
        main_db.session.flush()
        t1 = Target(scan_id=scan.id, type='domain', value='example.com')
        a1 = Asset(scan_id=scan.id, type='subdomain', value='test.example.com')
        main_db.session.add_all([t1, a1])
        main_db.session.commit()
        scan_id = scan.id

        response = test_client.get(f'/api/v1/scans/{scan_id}/graph', headers={'X-API-Key': test_user.api_key})
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert 'graph_definition' in response_data
    assert 'graph TD' in response_data['graph_definition']
    assert 'target1("example.com (domain)")' in response_data['graph_definition']
    assert 'asset1testexamplecom("test.example.com (subdomain)")' in response_data['graph_definition']
