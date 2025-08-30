import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from run_web import app, db
from cyberhunter_3d.web.models import Scan, Target, User

class TestReconV2(unittest.TestCase):
    def setUp(self):
        """Set up a test client and a test database."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app
        with self.app.app_context():
            db.create_all()
            user = User(id=1, username='testuser', password_hash='hash', otp_secret='secret')
            scan = Scan(id=1, user_id=1, status='RUNNING')
            target = Target(id=1, scan_id=1, value="example.com", type='domain')
            db.session.add_all([user, scan, target])
            db.session.commit()

    def tearDown(self):
        """Clean up the database after each test."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.save_to_json')
    @patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.PluginManager')
    def test_full_recon_pipeline_with_plugins(self, mock_plugin_manager, mock_save_json):
        """
        Integration test for the new plugin-based reconnaissance pipeline.
        """
        # 1. Setup Mocks
        mock_pm_instance = mock_plugin_manager.return_value
        mock_pm_instance.run_all_plugins.return_value = None

        # 2. Execute the function
        domain = "example.com"
        with self.app.app_context():
            output_files = enumerate_subdomains_v2(domain, scan_id=1, app=self.app)

        # 3. Assertions
        mock_pm_instance.run_all_plugins.assert_called_once()
        mock_save_json.assert_called_once()
        # You could add more detailed assertions here about the content of the context
        # that is passed to run_all_plugins if needed.

if __name__ == '__main__':
    unittest.main()
