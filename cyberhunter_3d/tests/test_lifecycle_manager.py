import unittest
from unittest.mock import patch, MagicMock
import pyotp
from cyberhunter_3d.core.lifecycle_manager import ScanLifecycleManager
from cyberhunter_3d.web.models import db, Scan, User, Target
from run_web import app, bcrypt

class TestLifecycleManager(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            # Create a user
            password_hash = bcrypt.generate_password_hash('password').decode('utf-8')
            otp_secret = pyotp.random_base32()
            user = User(username='testuser', password_hash=password_hash, otp_secret=otp_secret)
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @patch('cyberhunter_3d.core.lifecycle_manager.run_discovery_phase')
    @patch('cyberhunter_3d.core.lifecycle_manager.run_execution_phase')
    def test_scan_lifecycle_run(self, mock_run_execution, mock_run_discovery):
        """
        Test the full run of the scan lifecycle manager.
        """
        with self.app.app_context():
            # Create a scan
            scan = Scan(user_id=self.user_id, status='QUEUED')
            db.session.add(scan)
            db.session.commit()
            scan_id = scan.id

            # Create a target for the scan
            target = Target(value='example.com', type='domain', scan_id=scan_id)
            db.session.add(target)
            db.session.commit()

            # Mock the external functions to avoid running them
            def discovery_se(scan_id, app):
                s = Scan.query.get(scan_id)
                s.status = 'PENDING_REVIEW'
                db.session.commit()
            mock_run_discovery.side_effect = discovery_se

            def execution_se(scan_id, app):
                s = Scan.query.get(scan_id)
                s.status = 'COMPLETED'
                db.session.commit()
            mock_run_execution.side_effect = execution_se

            # Create and run the lifecycle manager
            manager = ScanLifecycleManager(scan_id, self.app)
            manager.run()

            # Assertions
            final_scan = Scan.query.get(scan_id)
            self.assertEqual(final_scan.status, 'COMPLETED')

            # Check if the mocks were called
            mock_run_discovery.assert_called_once_with(scan_id, self.app)
            mock_run_execution.assert_called_once_with(scan_id, self.app)

if __name__ == '__main__':
    unittest.main()
