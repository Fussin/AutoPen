import unittest
import os
import json
import shutil
from unittest.mock import patch, MagicMock
from run_web import app, db, bcrypt
from cyberhunter_3d.web.models import User, Scan, Target

from flask_login import login_user

class TestWebView(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.drop_all()

    @patch('run_web.bcrypt.check_password_hash', return_value=True)
    @patch('pyotp.TOTP.verify', return_value=True)
    def test_scan_results_view_with_url_data(self, mock_verify, mock_check_hash):
        with app.app_context():
            password_hash = bcrypt.generate_password_hash('password').decode('utf-8')
            user = User(username='testuser', password_hash=password_hash, otp_secret='secret')
            db.session.add(user)
            db.session.commit()

            scan = Scan(user_id=user.id)
            target = Target(value='example.com', type='domain')
            scan.targets.append(target)
            db.session.add(scan)
            db.session.commit()
            scan_id = scan.id

        with app.test_client() as client:
            # Simulate login
            client.post('/login', data={'username': 'testuser', 'password': 'password'})
            client.post('/verify-2fa', data={'token': '123456'})

            # Create mock results file
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
            response = client.get(f'/scan/{scan_id}')
            self.assertEqual(response.status_code, 200)

            # Check for new data in the response
            self.assertIn(b'Vulnerabilities', response.data)
            self.assertIn(b'Test Vuln', response.data)


        # Clean up mock files
        shutil.rmtree(results_dir)

            # Clean up mock files
            if os.path.exists(results_dir):
                shutil.rmtree(results_dir)


if __name__ == '__main__':
    unittest.main()
