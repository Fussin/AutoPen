import pytest
import json
from unittest.mock import patch, MagicMock
from run_web import app, db
from cyberhunter_3d.web.models import User, Scan, Asset

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    client = app.test_client()

    with app.app_context():
        db.create_all()
        # Create a test user
        user = User(username='testuser', password_hash='testhash', otp_secret='testotp')
        db.session.add(user)
        db.session.commit()

    yield client

    with app.app_context():
        db.drop_all()

def test_get_scans_api(client):
    """Tests the GET /api/v1/scans endpoint."""
    with app.app_context():
        user = User.query.first()
        api_key = user.api_key
        # Create a test scan
        scan = Scan(user_id=user.id, status='COMPLETED')
        db.session.add(scan)
        db.session.commit()
        scan_id = scan.id # Get the id while the session is active

    headers = {'X-API-Key': api_key}
    response = client.get('/api/v1/scans', headers=headers)

    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['id'] == scan_id

def test_get_scan_results_api(client):
    """Tests the GET /api/v1/scans/<id>/results endpoint."""
    with app.app_context():
        user = User.query.first()
        api_key = user.api_key
        scan = Scan(user_id=user.id, status='COMPLETED')
        db.session.add(scan)
        db.session.flush()
        # Create a test asset
        asset = Asset(scan_id=scan.id, type='subdomain', value='test.example.com', risk_level='High', cvss_score=8.5)
        db.session.add(asset)
        db.session.commit()
        scan_id = scan.id # Get the id while the session is active

    headers = {'X-API-Key': api_key}
    response = client.get(f'/api/v1/scans/{scan_id}/results', headers=headers)

    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data['assets']) == 1
    assert data['assets'][0]['value'] == 'test.example.com'
    assert data['assets'][0]['risk_level'] == 'High'
