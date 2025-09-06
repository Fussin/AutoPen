import unittest
import json
from unittest.mock import patch, MagicMock
from run_web import app, db
from cyberhunter_3d.web.models import User, Workspace, Scan, Target, Asset

class APITestCase(unittest.TestCase):
    def setUp(self):
        """Set up a test client and a test database."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()
            # Create a test user
            test_user = User(username='testuser', password_hash='somehash', otp_secret='secret')
            db.session.add(test_user)
            db.session.commit()
            self.api_key = test_user.api_key
            self.user_id = test_user.id

            # Create a test workspace
            workspace = Workspace(name="Test Workspace", owner_id=self.user_id)
            workspace.members.append(test_user)
            db.session.add(workspace)
            db.session.commit()
            self.workspace_id = workspace.id

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
        mock_executor = MagicMock()
        mock_get_executor.return_value = mock_executor

        payload = {
            "workspace_id": self.workspace_id,
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

        with app.app_context():
            scan = Scan.query.get(scan_id)
            self.assertIsNotNone(scan)
            self.assertEqual(scan.owner_id, self.user_id)
            self.assertEqual(scan.workspace_id, self.workspace_id)

        mock_executor.submit.assert_called_once()

    def test_get_scan_status_api(self):
        """Test getting scan status via the API."""
        with app.app_context():
            scan = Scan(owner_id=self.user_id, workspace_id=self.workspace_id, status='COMPLETED', results='Test summary')
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
            scan = Scan(owner_id=self.user_id, workspace_id=self.workspace_id, status='COMPLETED')
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

    def test_get_scan_graph_api(self):
        """Test getting scan graph data via the API."""
        with app.app_context():
            scan = Scan(owner_id=self.user_id, workspace_id=self.workspace_id, status='COMPLETED')
            db.session.add(scan)
            db.session.flush()
            t1 = Target(scan_id=scan.id, type='domain', value='example.com')
            a1 = Asset(scan_id=scan.id, type='subdomain', value='test.example.com')
            db.session.add_all([t1, a1])
            db.session.commit()
            scan_id = scan.id

            response = self.client.get(f'/api/v1/scans/{scan_id}/graph', headers={'X-API-Key': self.api_key})
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.data)
            self.assertIn('graph_definition', response_data)
            self.assertIn('graph TD', response_data['graph_definition'])
            self.assertIn('target1("example.com (domain)")', response_data['graph_definition'])
            self.assertIn('asset1testexamplecom("test.example.com (subdomain)")', response_data['graph_definition'])

if __name__ == '__main__':
    unittest.main()
