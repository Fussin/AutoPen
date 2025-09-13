import unittest
from unittest.mock import patch
import pyotp
from run_web import create_app
from cyberhunter_3d.web.models import db, User, Scan, Target, Asset, Vulnerability
from cyberhunter_3d.extensions import bcrypt

class Test3DVisualization(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            # Create a user for authentication
            password_hash = bcrypt.generate_password_hash('testpassword').decode('utf-8')
            user = User(username='testuser', password_hash=password_hash, otp_secret='testsecret')
            user.regenerate_api_key()
            db.session.add(user)
            db.session.commit()
            self.user = user

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @patch('cyberhunter_3d.core.scan_manager.run_discovery_phase')
    def test_graph_data_api_and_view(self, mock_run_discovery_phase):
        with self.app.app_context():
            user = User.query.filter_by(username='testuser').first()
            self.assertIsNotNone(user)
            self.assertIsNotNone(user.api_key)

            # Login the user
            with self.client:
                self.client.post('/login', data={'username': 'testuser', 'password': 'testpassword'})
                totp = pyotp.TOTP(user.otp_secret)
                self.client.post('/verify-2fa', data={'token': totp.now()})

            # Create a scan
            scan = Scan(user_id=user.id, status='COMPLETED')
            db.session.add(scan)
            db.session.commit()

            # Create assets and vulnerabilities
            asset1 = Asset(scan_id=scan.id, value='example.com', type='DOMAIN')
            asset2 = Asset(scan_id=scan.id, value='192.168.1.1', type='IP_ADDRESS')
            db.session.add_all([asset1, asset2])
            db.session.commit()

            vuln1 = Vulnerability(asset_id=asset1.id, title='SQL Injection', severity='High', scan_id=scan.id, description='SQL Injection vulnerability found.')
            vuln2 = Vulnerability(asset_id=asset1.id, title='XSS', severity='Medium', scan_id=scan.id, description='XSS vulnerability found.')
            vuln3 = Vulnerability(asset_id=asset2.id, title='Open Port', severity='Low', scan_id=scan.id, description='Open port vulnerability found.')
            db.session.add_all([vuln1, vuln2, vuln3])
            db.session.commit()

            # Test the API endpoint
            response = self.client.get(f'/api/v1/scans/{scan.id}/graph_data', headers={'X-API-Key': user.api_key})
            self.assertEqual(response.status_code, 200)
            data = response.get_json()

            # Verify the structure of the response
            self.assertIn('nodes', data)
            self.assertIn('links', data)

            # Verify the content of the response
            self.assertEqual(len(data['nodes']), 6)  # 1 scan + 2 assets + 3 vulnerabilities
            self.assertEqual(len(data['links']), 5)  # 2 scan->asset + 3 asset->vuln

            # Test the graph view page
            response = self.client.get(f'/scan/{scan.id}/graph_view', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)

            self.assertIn('<div id="3d-graph"', html)
            self.assertIn('ForceGraph3D()', html)

if __name__ == '__main__':
    unittest.main()
