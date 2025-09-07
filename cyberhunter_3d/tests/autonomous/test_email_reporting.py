import sys
import os
import unittest.mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from run_web import app, db, bcrypt
from cyberhunter_3d.web.models import User, Scan
from cyberhunter_3d.core.post_scan_operations import run_post_scan_operations
from cyberhunter_3d.core.output_manager import OutputManager
from pathlib import Path

def setup_test_db():
    """Sets up a clean database for the test."""
    if os.path.exists('cyberhunter.db'):
        os.remove('cyberhunter.db')
    db.create_all()
    password_hash = bcrypt.generate_password_hash('password').decode('utf-8')
    otp_secret = "FWPQ7CKOCOA7P4S7IS3CXONMB756FAED"
    user = User(
        username='test',
        password_hash=password_hash,
        otp_secret=otp_secret,
        email='test@example.com',
        is_email_notifications_enabled=True
    )
    db.session.add(user)
    db.session.commit()
    print("Test database set up successfully.")

class TestEmailReporting(unittest.TestCase):
    def test_email_reporting(self):
        with app.app_context():
            setup_test_db()
            user = User.query.filter_by(username='test').first()
            scan = Scan(user_id=user.id)
            db.session.add(scan)
            db.session.commit()

            om = OutputManager.create_for_timestamp(Path("scan_results"))
            scan.output_dir = str(om.base_dir)
            db.session.commit()

            with unittest.mock.patch('cyberhunter_3d.core.post_scan_operations.send_report_email') as mock_send_email:
                # We also need to mock the other post-scan functions to avoid errors
                with unittest.mock.patch('cyberhunter_3d.core.post_scan_operations.backup_creation'):
                    with unittest.mock.patch('cyberhunter_3d.core.post_scan_operations.final_validation'):
                        with unittest.mock.patch('cyberhunter_3d.core.post_scan_operations.data_archival'):
                            with unittest.mock.patch('cyberhunter_3d.core.post_scan_operations.integration_updates'):
                                with unittest.mock.patch('cyberhunter_3d.core.post_scan_operations.analytics_update'):
                                    with unittest.mock.patch('cyberhunter_3d.core.post_scan_operations.schedule_next_scan'):
                                        with unittest.mock.patch('cyberhunter_3d.core.post_scan_operations.monitoring_activation'):
                                            with unittest.mock.patch('cyberhunter_3d.core.post_scan_operations.cleanup_operations'):
                                                with unittest.mock.patch('cyberhunter_3d.core.post_scan_operations.session_termination'):
                                                    with unittest.mock.patch('cyberhunter_3d.core.post_scan_operations.platform_logout'):
                                                        with unittest.mock.patch('cyberhunter_3d.core.post_scan_operations.session_closed'):
                                                            run_post_scan_operations(scan.id, app, om)

                assert mock_send_email.called
                print("Test PASSED: send_report_email was called.")

                # Check the arguments
                args, kwargs = mock_send_email.call_args
                self.assertEqual(args[0], 'test@example.com')
                self.assertEqual(args[1].id, scan.id)
                self.assertTrue(args[2].endswith('.pdf'))
                print("Test PASSED: send_report_email was called with the correct arguments.")

if __name__ == '__main__':
    unittest.main()
