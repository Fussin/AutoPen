import unittest
import os
import json
import shutil
from unittest.mock import patch, MagicMock
from run_web import app, db
from cyberhunter_3d.web.models import User, Scan, Target

from flask_login import login_user

class TestWebView(unittest.TestCase):

    @patch('run_web.bcrypt.generate_password_hash', return_value=b'hashed_password')
    def setUp(self, mock_bcrypt):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for testing forms
        self.app = app.test_client()
        with app.app_context():
            db.create_all()
            user = User(username='testuser', password_hash=b'hashed_password', otp_secret='secret')
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

        # Simulate login
        with patch('run_web.bcrypt.check_password_hash', return_value=True):
            self.app.post('/login', data={'username': 'testuser', 'password': 'password'})
        with patch('pyotp.TOTP.verify', return_value=True):
            self.app.post('/verify-2fa', data={'token': '123456'})


    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_scan_results_view_with_url_data(self):
        with app.app_context():
            # Create a scan
            scan = Scan(user_id=self.user_id)
            target = Target(value='example.com', type='domain', scan_id=scan.id)
            scan.targets.append(target)
            db.session.add(scan)
            db.session.commit()
            scan_id = scan.id

            # Create a mock results directory and report file
            from cyberhunter_3d.utils.file_utils import get_results_dir
            from cyberhunter_3d.core.reconnaissance.utils import load_config
            config = load_config()
            results_dir = get_results_dir('example.com', scan_id)
            os.makedirs(results_dir, exist_ok=True)

            mock_report_data = {
                "url_discovery": {
                    "alive_urls": ["http://alive.example.com"],
                    "dead_urls": ["http://dead.example.com"],
                    "redirect_urls": ["http://redirect.example.com"],
                    "parameters": ["id", "page"]
                },
                "vulnerabilities": [
                    {"info": {"name": "Test Vuln", "severity": "high"}, "host": "http://alive.example.com", "template-id": "test-template"}
                ]
            }
            report_path = os.path.join(results_dir, config['final_recon_file'])
            with open(report_path, 'w') as f:
                json.dump(mock_report_data, f)

        # Make request to the view
        response = self.app.get(f'/scan/{scan_id}')
        self.assertEqual(response.status_code, 200)

        # Check for new data in the response
        self.assertIn(b'Vulnerabilities', response.data)
        self.assertIn(b'Test Vuln', response.data)
        self.assertIn(b'Discovered URLs', response.data)
        self.assertIn(b'http://alive.example.com', response.data)
        self.assertIn(b'Discovered Parameters', response.data)
        self.assertIn(b'id', response.data)

        # Clean up mock files
        shutil.rmtree(results_dir)

if __name__ == '__main__':
    unittest.main()
