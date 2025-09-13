import pytest
from unittest.mock import MagicMock, patch
from collections import namedtuple
import socket

from flask import Flask
from cyberhunter_3d.core.decision_tree import DecisionTree

@pytest.fixture
def test_app():
    """A pytest fixture to create a Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def mock_scan():
    """A pytest fixture to create a mock scan object."""
    mock_scan_instance = MagicMock()
    mock_scan_instance.id = 1
    mock_scan_instance.in_scope_rules = ""
    mock_scan_instance.out_of_scope_rules = ""
    TargetTuple = namedtuple('Target', ['value', 'type'])
    mock_scan_instance.targets = [TargetTuple(value='example.com', type='domain')]
    return mock_scan_instance

@patch('cyberhunter_3d.core.decision_tree.db')
@patch('cyberhunter_3d.core.decision_tree.socket')
@patch('cyberhunter_3d.core.decision_tree.enumerate_subdomains_v2')
def test_domain_processing_flow(mock_enumerate_subdomains, mock_socket, mock_db, test_app, mock_scan):
    """Test the complete flow for a domain target."""
    with test_app.app_context():
        # --- Mocks Setup ---
        mock_db.session.get.return_value = mock_scan

        mock_enumerate_subdomains.return_value = [
            {'value': 'www.example.com', 'type': 'subdomain'},
            {'value': 'api.example.com', 'type': 'subdomain'},
            {'value': 'dead.example.com', 'type': 'subdomain'}
        ]

        def gethostbyname_ex_se(hostname):
            if hostname == 'www.example.com':
                return ('www.example.com', [], ['1.1.1.1'])
            elif hostname == 'api.example.com':
                return ('api.example.com', [], ['2.2.2.2'])
            else:
                raise socket.gaierror

        mock_socket.gethostbyname_ex.side_effect = gethostbyname_ex_se
        mock_socket.gaierror = socket.gaierror

        # --- Test Execution ---
        dt = DecisionTree(scan_id=1, app=test_app)
        domain_target = mock_scan.targets[0]
        dt.process_target(domain_target)

        # --- Assertions ---
        mock_enumerate_subdomains.assert_called_once_with('example.com')
        discovered_assets = dt.discovered_assets
        assert {'type': 'subdomain', 'value': 'www.example.com'} in discovered_assets
        assert {'type': 'ip_address', 'value': '1.1.1.1'} in discovered_assets
        assert {'type': 'subdomain', 'value': 'api.example.com'} in discovered_assets
        assert {'type': 'ip_address', 'value': '2.2.2.2'} in discovered_assets
        assert {'type': 'subdomain', 'value': 'dead.example.com'} not in discovered_assets
