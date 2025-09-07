import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from run_web import app, db, bcrypt
from cyberhunter_3d.web.models import User, Scan, Vulnerability
from cyberhunter_3d.core.analysis.prioritization_engine import prioritize_vulnerabilities, SEVERITY_TO_PRIORITY

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

class TestPrioritization(unittest.TestCase):
    def test_prioritization(self):
        with app.app_context():
            setup_test_db()
            user = User.query.filter_by(username='test').first()
            scan = Scan(user_id=user.id)
            db.session.add(scan)
            db.session.flush()

            # Create mock vulnerabilities
            vulns_to_create = [
                Vulnerability(title='Crit Vuln', severity='critical', description='desc', scan_id=scan.id),
                Vulnerability(title='High Vuln', severity='high', description='desc', scan_id=scan.id),
                Vulnerability(title='Medium Vuln', severity='medium', description='desc', scan_id=scan.id),
                Vulnerability(title='Low Vuln', severity='low', description='desc', scan_id=scan.id),
                Vulnerability(title='Info Vuln', severity='info', description='desc', scan_id=scan.id),
                Vulnerability(title='Unknown Vuln', severity='unknown', description='desc', scan_id=scan.id),
            ]
            db.session.add_all(vulns_to_create)
            db.session.commit()

            # Run the prioritization engine
            prioritize_vulnerabilities(scan.id)

            # Assert that priorities have been set correctly
            for vuln in vulns_to_create:
                db.session.refresh(vuln) # Refresh from DB
                expected_priority = SEVERITY_TO_PRIORITY[vuln.severity]
                self.assertEqual(vuln.priority, expected_priority)
                print(f"Test PASSED for severity '{vuln.severity}': Priority is {vuln.priority}")

if __name__ == '__main__':
    unittest.main()
