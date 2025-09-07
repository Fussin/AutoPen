import sys
import os
import unittest.mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from run_web import app, db, bcrypt
from cyberhunter_3d.web.models import User, Scan, Asset, Vulnerability
from cyberhunter_3d.core.feeds.feed_manager import check_for_new_targets

from flask_bcrypt import Bcrypt

def setup_test_db(app_context):
    """Sets up a clean database for the test."""
    if os.path.exists('cyberhunter.db'):
        os.remove('cyberhunter.db')
    db.create_all()
    bcrypt = Bcrypt(app_context)
    password_hash = bcrypt.generate_password_hash('password').decode('utf-8')
    otp_secret = "FWPQ7CKOCOA7P4S7IS3CXONMB756FAED"
    user = User(username='test', password_hash=password_hash, otp_secret=otp_secret)
    db.session.add(user)
    db.session.commit()
    print("Test database set up successfully.")

class MockDecisionTree:
    def __init__(self, scan_id, app):
        self.scan_id = scan_id
        self.discovered_assets = []
    def process_target(self, target):
        pass
    def persist_discovered_assets(self):
        asset1 = Asset(type='subdomain', value='in-scope.test.com', scan_id=self.scan_id, is_approved_for_scan=False)
        db.session.add(asset1)
        db.session.commit()
        return 1, 0
    def _is_subdomain_alive(self, s):
        return ["127.0.0.1"]

def mock_get_hackerone_scopes(api_user, api_key):
    return [{'name': 'test-program-full-flow', 'targets': ['test.com'], 'in_scope_rules': '*.test.com', 'out_of_scope_rules': 'out-of-scope.test.com'}]

def mock_run_gospider_scan(target_site):
    return [f"{target_site}/discovered_path"]

def mock_run_nuclei_scan(target_url, output_dir):
    return [{"info": {"name": "Mock Nuclei Finding", "severity": "high", "description": "A mock finding."}}]

def run_synchronously(func, *args, **kwargs):
    func(*args, **kwargs)
    return unittest.mock.MagicMock()

@unittest.mock.patch('cyberhunter_3d.core.scan_manager.run_gospider_scan', mock_run_gospider_scan)
@unittest.mock.patch('cyberhunter_3d.core.scan_manager.run_nuclei_scan', mock_run_nuclei_scan)
@unittest.mock.patch('cyberhunter_3d.core.scan_manager.executor.submit', side_effect=run_synchronously)
@unittest.mock.patch('cyberhunter_3d.core.feeds.feed_manager.executor.submit', side_effect=run_synchronously)
@unittest.mock.patch('cyberhunter_3d.core.scan_manager.DecisionTree', MockDecisionTree)
@unittest.mock.patch('cyberhunter_3d.core.feeds.feed_manager.get_hackerone_scopes', new=mock_get_hackerone_scopes)
def test_full_workflow(mock_scan_manager_submit, mock_feed_manager_submit):
    with app.app_context():
        setup_test_db(app)

        user = User.query.filter_by(username='test').first()
        user.hackerone_username = 'test'
        user.hackerone_api_key = 'dummy-key'
        db.session.commit()

        check_for_new_targets(app)

        scan = Scan.query.filter_by(hackerone_program_handle='test-program-full-flow').first()
        assert scan is not None, "Scan was not created"
        print("Test PASSED: Scan was created.")

        url_asset = Asset.query.filter_by(scan_id=scan.id, type='url').first()
        assert url_asset is not None, "URL asset was not created"
        assert url_asset.value == "https://in-scope.test.com/discovered_path"
        print("Test PASSED: URL asset was created correctly.")

        vuln = Vulnerability.query.filter_by(scan_id=scan.id).first()
        assert vuln is not None, "Vulnerability was not created"
        assert vuln.title == "Mock Nuclei Finding"
        print("Test PASSED: Vulnerability was created correctly.")

        assert vuln.priority == 2, f"Priority was not set correctly, got {vuln.priority}"
        print("Test PASSED: Priority was set correctly.")

if __name__ == '__main__':
    test_full_workflow()
