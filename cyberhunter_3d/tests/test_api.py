import unittest
import json
from unittest.mock import patch, MagicMock
from run_web import app, db
from cyberhunter_3d.web.models import User, Scan, Target, Asset

class APITestCase(unittest.TestCase):
    def setUp(self):
        """Set up a test client and a test database."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()
            # Create a test user
            self.test_user = User(username='testuser', password_hash='somehash', otp_secret='secret')
            db.session.add(self.test_user)
            db.session.commit()
            self.api_key = self.test_user.api_key

    def tearDown(self):
        """Clean up the database after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_ping_unauthorized(self):
        """Test that ping endpoint requires an API key."""
        response = self.client.get('/api/v1/ping')
        self.assertEqual(response.status_code, 401)

    def test_ping_authorized(self):
        """Test that ping endpoint works with a valid API key."""
        response = self.client.get('/api/v1/ping', headers={'X-API-Key': self.api_key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data)['message'], 'pong')

    @patch('cyberhunter_3d.web.api.get_executor')
    def test_create_scan_api(self, mock_get_executor):
        """Test creating a scan via the API."""
        # Mock the executor to avoid running background tasks
        mock_executor = MagicMock()
        mock_get_executor.return_value = mock_executor

        payload = {
            "targets": ["example.com", "1.1.1.1"],
            "in_scope_rules": "*.example.com"
        }
        response = self.client.post('/api/v1/scans',
                                    headers={'X-API-Key': self.api_key},
                                    data=json.dumps(payload),
                                    content_type='application/json')

        self.assertEqual(response.status_code, 202)
        response_data = json.loads(response.data)
        self.assertIn('scan_id', response_data)
        scan_id = response_data['scan_id']

        # Verify the scan was created in the DB within an app context
        with app.app_context():
            scan = Scan.query.get(scan_id)
            self.assertIsNotNone(scan)
            self.assertEqual(scan.user_id, self.test_user.id)

        # Verify that the background task was called
        mock_executor.submit.assert_called_once()

    def test_get_scan_status_api(self):
        """Test getting scan status via the API."""
        with app.app_context():
            # First, create a scan to check
            scan = Scan(user_id=self.test_user.id, status='COMPLETED', results='Test summary')
            db.session.add(scan)
            db.session.commit()
            scan_id = scan.id

        response = self.client.get(f'/api/v1/scans/{scan_id}/status', headers={'X-API-Key': self.api_key})
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['status'], 'COMPLETED')
        self.assertEqual(response_data['summary'], 'Test summary')

    def test_get_scan_results_api(self):
        """Test getting scan results via the API."""
        with app.app_context():
            # Create a scan and some assets
            scan = Scan(user_id=self.test_user.id, status='COMPLETED')
            db.session.add(scan)
            db.session.flush()
            asset1 = Asset(scan_id=scan.id, type='subdomain', value='test.example.com')
            asset2 = Asset(scan_id=scan.id, type='ip_address', value='1.2.3.4')
            db.session.add_all([asset1, asset2])
            db.session.commit()
            scan_id = scan.id

        response = self.client.get(f'/api/v1/scans/{scan_id}/results', headers={'X-API-Key': self.api_key})
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(len(response_data['assets']), 2)
        self.assertEqual(response_data['assets'][0]['value'], 'test.example.com')

if __name__ == '__main__':
    unittest.main()
