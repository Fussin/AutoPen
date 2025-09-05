import unittest
from unittest.mock import patch, MagicMock

# It's important to get the app and db from a central place.
# The project structure makes this a bit tricky, so we'll import from run_web.
from run_web import app, db
from cyberhunter_3d.web.models import User, Scan, Target
from cyberhunter_3d.core.phase_manager import PhaseManager

class PhaseManagerTestCase(unittest.TestCase):
    def setUp(self):
        """Set up a test environment before each test."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Use in-memory SQLite DB
        self.client = app.test_client()

        with app.app_context():
            db.create_all()
            # 1. Create a test user
            test_user = User(username='testuser', password_hash='somehash', otp_secret='secret')
            db.session.add(test_user)
            db.session.commit()

            # 2. Create a test scan and target
            test_scan = Scan(user_id=test_user.id, status='QUEUED')
            db.session.add(test_scan)
            db.session.commit() # Commit to get the scan ID

            test_target = Target(value='example.com', type='domain', scan_id=test_scan.id)
            db.session.add(test_target)
            db.session.commit()

            self.test_scan_id = test_scan.id
            self.app = app

    def tearDown(self):
        """Clean up the database after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    @patch('cyberhunter_3d.core.phase_manager.run_execution_phase')
    @patch('cyberhunter_3d.core.phase_manager.run_discovery_phase')
    def test_run_scan_orchestrates_phases(self, mock_run_discovery, mock_run_execution):
        """
        Test that PhaseManager.run_scan() calls the core functions for the implemented phases.
        """
        # We need to be inside an app context to run the phase manager
        with self.app.app_context():
            # Instantiate the manager for our test scan
            phase_manager = PhaseManager(scan_id=self.test_scan_id, app=self.app)

            # Run the full scan process
            phase_manager.run_scan()

        # Assert that the mocked functions (our implemented phases) were called exactly once
        mock_run_discovery.assert_called_once_with(self.test_scan_id, self.app)
        mock_run_execution.assert_called_once_with(self.test_scan_id, self.app)

        # You could also check the logs or the final state of the scan in the DB
        with self.app.app_context():
            final_scan = Scan.query.get(self.test_scan_id)
            # Note: The main.py script updates status to COMPLETED, but the PhaseManager itself doesn't.
            # This is fine, as we are testing the manager in isolation.
            # The status will be whatever the last mocked function sets it to.
            # Since we mock the functions, they don't change the status.
            self.assertIsNotNone(final_scan)


if __name__ == '__main__':
    unittest.main()
