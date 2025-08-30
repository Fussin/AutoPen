import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from cyberhunter_3d.web.models import db, Scan, Target
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.plugins.manager import PluginManager

class TestReconV2(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        with self.app.app_context():
            db.create_all()
            # Create a dummy scan so the function can find it
            scan = Scan(id=1, status="RUNNING", user_id=1)
            target = Target(scan_id=1, value="example.com")
            scan.targets.append(target)
            db.session.add(scan)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.save_to_json')
    @patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.PluginManager')
    def test_full_recon_pipeline_with_plugins(self, mock_plugin_manager, mock_save_json):
        """
        Integration test for the new plugin-based reconnaissance pipeline.
        """
        # 1. Setup
        mock_pm_instance = mock_plugin_manager.return_value
        mock_pm_instance.run_all_plugins = MagicMock()

        # 2. Execute the function
        domain = "example.com"
        with self.app.app_context():
            output_files = enumerate_subdomains_v2(domain, scan_id=1, app=self.app)

        # 3. Assertions
        mock_pm_instance.run_all_plugins.assert_called_once()
        mock_save_json.assert_called()

if __name__ == '__main__':
    unittest.main()
