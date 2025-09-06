import unittest
from unittest.mock import patch, MagicMock, ANY
from collections import namedtuple
import socket

# Mock the Flask app and db
from flask import Flask

# It's important to mock db before it's used by the models
db_mock = MagicMock()

# Mock the models before importing the modules that use them
mock_user = MagicMock()
mock_scan = MagicMock()
mock_target = MagicMock()
mock_asset = MagicMock()

# Apply patches to the modules where they are defined
user_patch = patch('cyberhunter_3d.web.models.User', mock_user)
scan_patch = patch('cyberhunter_3d.web.models.Scan', mock_scan)
target_patch = patch('cyberhunter_3d.web.models.Target', mock_target)
asset_patch = patch('cyberhunter_3d.web.models.Asset', mock_asset)
db_patch = patch('cyberhunter_3d.web.models.db', db_mock)

# Start patches
user_patch.start()
scan_patch.start()
target_patch.start()
asset_patch.start()
db_patch.start()

from cyberhunter_3d.core.decision_tree import DecisionTree

class TestDecisionTree(unittest.TestCase):

    def setUp(self):
        """Set up a mock Flask app and a mock scan for each test."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True

        # Mock a scan object with targets
        self.mock_scan_instance = MagicMock()
        self.mock_scan_instance.id = 1
        self.mock_scan_instance.in_scope_rules = ""
        self.mock_scan_instance.out_of_scope_rules = ""

        TargetTuple = namedtuple('Target', ['value', 'type'])
        self.mock_scan_instance.targets = [
            TargetTuple(value='example.com', type='domain'),
            TargetTuple(value='8.8.8.8', type='ip_address')
        ]

        # Configure the mock Scan model to return our mock instance
        mock_scan.query.get.return_value = self.mock_scan_instance

    @patch('cyberhunter_3d.core.decision_tree.socket')
    @patch('cyberhunter_3d.core.decision_tree.enumerate_subdomains_v2')
    def test_domain_processing_flow(self, mock_enumerate_subdomains, mock_socket):
        """Test the complete flow for a domain target."""
        with self.app.app_context():
            # --- Mocks Setup ---
            # Mock subdomain enumeration to return a list of subdomains
            mock_enumerate_subdomains.return_value = [
                {'value': 'www.example.com', 'type': 'subdomain'},
                {'value': 'api.example.com', 'type': 'subdomain'},
                {'value': 'dead.example.com', 'type': 'subdomain'}
            ]

            # Mock socket to simulate which subdomains are alive
            def gethostbyname_ex_se(hostname):
                if hostname == 'www.example.com':
                    return ('www.example.com', [], ['1.1.1.1'])
                elif hostname == 'api.example.com':
                    return ('api.example.com', [], ['2.2.2.2'])
                # 'dead.example.com' will raise gaierror, simulating a dead host
                # The wildcard check will also raise gaierror, simulating no wildcard
                else:
                    raise socket.gaierror

            mock_socket.gethostbyname_ex.side_effect = gethostbyname_ex_se
            mock_socket.gaierror = socket.gaierror

            # --- Test Execution ---
            # Instantiate the decision tree
            dt = DecisionTree(scan_id=1, app=self.app)

            # Process the domain target
            domain_target = self.mock_scan_instance.targets[0]
            dt.process_target(domain_target)

            # --- Assertions ---
            # Check that subdomain enumeration was called
            mock_enumerate_subdomains.assert_called_once_with('example.com')

            # Check that assets were added for alive subdomains and their IPs
            discovered_assets = dt.discovered_assets
            self.assertIn({'type': 'subdomain', 'value': 'www.example.com'}, discovered_assets)
            self.assertIn({'type': 'ip_address', 'value': '1.1.1.1'}, discovered_assets)
            self.assertIn({'type': 'subdomain', 'value': 'api.example.com'}, discovered_assets)
            self.assertIn({'type': 'ip_address', 'value': '2.2.2.2'}, discovered_assets)

            # Check that the dead subdomain was not added
            self.assertNotIn({'type': 'subdomain', 'value': 'dead.example.com'}, discovered_assets)

    def tearDown(self):
        """Stop all patches after each test."""
        mock_scan.query.get.reset_mock()

# This allows running the tests directly
if __name__ == '__main__':
    unittest.main()
