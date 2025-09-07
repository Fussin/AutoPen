import sys
import os
import unittest.mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from run_web import app, db
from cyberhunter_3d.web.models import User, Scan, Asset
from cyberhunter_3d.core.scan_manager import run_discovery_phase

# Mock the DecisionTree to return some assets
class MockDecisionTree:
    def __init__(self, scan_id, app):
        self.discovered_assets = [
            {'type': 'subdomain', 'value': 'in-scope.example.com'},
            {'type': 'subdomain', 'value': 'out-of-scope.example.com'},
        ]
    def process_target(self, target):
        pass
    def persist_discovered_assets(self):
        # This part is complex, we will just manually create the assets
        return 2, 0
    def _is_subdomain_alive(self, s):
        return ["127.0.0.1"]

@unittest.mock.patch('cyberhunter_3d.core.scan_manager.DecisionTree', MockDecisionTree)
@unittest.mock.patch('cyberhunter_3d.core.scan_manager.run_execution_phase')
def test_autonomous_workflow(mock_run_execution):
    with app.app_context():
        user = User.query.filter_by(username='test').first()
        if not user:
            print("Error: test user not found.")
            exit(1)

        scan = Scan(
            user_id=user.id,
            status='QUEUED',
            in_scope_rules='*.example.com',
            out_of_scope_rules='out-of-scope.example.com'
        )
        db.session.add(scan)
        db.session.flush()

        # Manually create assets that would be discovered
        asset1 = Asset(type='subdomain', value='in-scope.example.com', scan_id=scan.id, is_approved_for_scan=False)
        asset2 = Asset(type='subdomain', value='out-of-scope.example.com', scan_id=scan.id, is_approved_for_scan=False)
        db.session.add_all([asset1, asset2])
        db.session.commit()

        print(f"Created Scan ID: {scan.id}")

        run_discovery_phase(scan.id, app)

        # Check if run_execution_phase was called
        if mock_run_execution.called:
            print("Test PASSED: run_execution_phase was called.")
        else:
            print("Test FAILED: run_execution_phase was not called.")

        # Check if the asset was approved
        approved_asset = Asset.query.get(asset1.id)
        if approved_asset.is_approved_for_scan:
            print("Test PASSED: In-scope asset was approved.")
        else:
            print("Test FAILED: In-scope asset was not approved.")

        unapproved_asset = Asset.query.get(asset2.id)
        if not unapproved_asset.is_approved_for_scan:
            print("Test PASSED: Out-of-scope asset was not approved.")
        else:
            print("Test FAILED: Out-of-scope asset was approved.")

if __name__ == '__main__':
    test_autonomous_workflow()
