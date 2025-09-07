import sys
import os
import unittest.mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from run_web import app, db, bcrypt
from cyberhunter_3d.web.models import User, Scan, Asset
from cyberhunter_3d.core.scan_manager import VulnerabilityScanningPhase
from cyberhunter_3d.core.output_manager import OutputManager
from pathlib import Path

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

def mock_run_gospider_scan(target_site):
    print(f"MOCK: gospider scan for {target_site}")
    return ["https://in-scope.example.com/page1", "https://in-scope.example.com/page2"]

@unittest.mock.patch('cyberhunter_3d.core.scan_manager.run_gospider_scan', mock_run_gospider_scan)
def test_url_discovery_workflow():
    with app.app_context():
        setup_test_db()
        user = User.query.filter_by(username='test').first()

        scan = Scan(user_id=user.id, status='RUNNING')
        db.session.add(scan)
        db.session.flush()

        asset = Asset(type='domain', value='in-scope.example.com', scan_id=scan.id, is_approved_for_scan=True)
        db.session.add(asset)
        db.session.commit()

        om = OutputManager.create_for_timestamp(Path("scan_results"))
        scan.output_dir = str(om.base_dir)
        db.session.commit()

        phase = VulnerabilityScanningPhase(scan.id, app, om)

        with unittest.mock.patch.object(phase, '_run_nuclei_on_targets') as mock_run_nuclei:
            phase.run()

            # 1. Assert that new URL assets were created
            url_assets = Asset.query.filter_by(scan_id=scan.id, type='url').all()
            assert len(url_assets) == 2
            print("Test PASSED: Correct number of URL assets created.")

            # 2. Assert that Nuclei was called with the correct targets
            assert mock_run_nuclei.called
            call_args = mock_run_nuclei.call_args[0][0] # Get the first argument of the call

            # The argument is a list of tuples (asset, url)
            passed_urls = {item[1] for item in call_args}
            expected_urls = {"https://in-scope.example.com/page1", "https://in-scope.example.com/page2"}

            assert passed_urls == expected_urls
            print("Test PASSED: Nuclei was called with the correct URLs.")

if __name__ == '__main__':
    test_url_discovery_workflow()
