import sys
import os
import unittest.mock
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from run_web import app, db, bcrypt
from cyberhunter_3d.web.models import User, Scan, Asset, Vulnerability
from cyberhunter_3d.core.scan_manager import VulnerabilityScanningPhase
from cyberhunter_3d.core.output_manager import OutputManager
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

def mock_run_sqlmap_scan(target_url, output_dir):
    """Mocks the sqlmap scan and creates a dummy log file indicating a vulnerability."""
    print(f"MOCK: sqlmap scan for {target_url}")
    log_path = output_dir / "log"
    with open(log_path, 'w') as f:
        f.write("some log data... and the target is vulnerable.")
    return output_dir

@unittest.mock.patch('cyberhunter_3d.core.scan_manager.run_sqlmap_scan', new=mock_run_sqlmap_scan)
@unittest.mock.patch('cyberhunter_3d.core.scan_manager.run_nuclei_scan', return_value=[])
def test_sqlmap_integration(mock_nuclei):
    with app.app_context():
        setup_test_db(app)
        user = User.query.filter_by(username='test').first()
        scan = Scan(user_id=user.id)
        db.session.add(scan)
        db.session.flush()

        # Create a URL asset to be scanned
        asset = Asset(type='url', value='http://test.com/vuln.php?id=1', scan_id=scan.id, is_approved_for_scan=True)
        db.session.add(asset)
        db.session.commit()

        om = OutputManager.create_for_timestamp(Path("scan_results"))
        scan.output_dir = str(om.base_dir)
        db.session.commit()

        phase = VulnerabilityScanningPhase(scan.id, app, om)
        phase.run()

        # Assert that a sqlmap vulnerability was created
        vuln = Vulnerability.query.filter_by(scan_id=scan.id, source='sqlmap').first()
        assert vuln is not None, "No sqlmap vulnerability was created"
        assert vuln.severity == 'critical'
        print("Test PASSED: sqlmap vulnerability was created correctly.")

if __name__ == '__main__':
    test_sqlmap_integration()
