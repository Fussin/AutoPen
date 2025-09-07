import sys
import os
import unittest.mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from run_web import app, db, bcrypt
from cyberhunter_3d.web.models import User, Scan, Asset
from cyberhunter_3d.core.feeds.feed_manager import check_for_new_targets

def setup_test_db():
    """Sets up a clean database for the test."""
    if os.path.exists('cyberhunter.db'):
        os.remove('cyberhunter.db')
    db.create_all()
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
        asset2 = Asset(type='subdomain', value='out-of-scope.test.com', scan_id=self.scan_id, is_approved_for_scan=False)
        db.session.add_all([asset1, asset2])
        db.session.commit()
        return 2, 0
    def _is_subdomain_alive(self, s):
        return ["127.0.0.1"]

def mock_get_hackerone_scopes(api_user, api_key):
    return [
        {
            'name': 'test-program-full-flow',
            'targets': ['test.com'],
            'in_scope_rules': '*.test.com',
            'out_of_scope_rules': 'out-of-scope.test.com'
        }
    ]

def run_synchronously(func, *args, **kwargs):
    """Replaces executor.submit to run tasks in the same thread for testing."""
    func(*args, **kwargs)
    return unittest.mock.MagicMock()

@unittest.mock.patch('cyberhunter_3d.core.scan_manager.executor.submit', side_effect=run_synchronously)
@unittest.mock.patch('cyberhunter_3d.core.feeds.feed_manager.executor.submit', side_effect=run_synchronously)
@unittest.mock.patch('cyberhunter_3d.core.scan_manager.DecisionTree', MockDecisionTree)
@unittest.mock.patch('cyberhunter_3d.core.scan_manager.run_execution_phase')
@unittest.mock.patch('cyberhunter_3d.core.feeds.feed_manager.get_hackerone_scopes', new=mock_get_hackerone_scopes)
def test_full_workflow(mock_run_execution, mock_scan_manager_submit, mock_feed_manager_submit):
    with app.app_context():
        setup_test_db()

        user = User.query.filter_by(username='test').first()
        user.hackerone_username = 'test'
        user.hackerone_api_key = 'dummy-key'
        db.session.commit()

        check_for_new_targets(app)

        if mock_run_execution.call_count == 1:
            print("Test PASSED: run_execution_phase was called once.")
        else:
            print(f"Test FAILED: run_execution_phase was called {mock_run_execution.call_count} times.")

        scan = Scan.query.filter_by(hackerone_program_handle='test-program-full-flow').first()
        approved_asset = Asset.query.filter_by(scan_id=scan.id, value='in-scope.test.com').first()

        if approved_asset and approved_asset.is_approved_for_scan:
            print("Test PASSED: In-scope asset was approved.")
        else:
            print("Test FAILED: In-scope asset was not approved.")

if __name__ == '__main__':
    test_full_workflow()
