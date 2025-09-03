import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from flask import Flask
from freezegun import freeze_time

from cyberhunter_3d.web.models import db, Scan, Asset, Target, User, Schedule, now_utc
from cyberhunter_3d.core.scheduler.service import SchedulerService

class TestSchedulerService(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.drop_all()

    @patch('cyberhunter_3d.core.scheduler.service.launch_scan')
    def test_check_and_run_scans(self, mock_launch_scan):
        """Test the core logic of the scheduler job."""
        with self.app.app_context():
            # --- Setup Data ---
            user = User(username='testuser', password_hash='123', otp_secret='secret')
            scan = Scan(user=user, status='COMPLETED')
            target = Target(value='example.com', scan=scan)
            db.session.add_all([user, scan, target])
            db.session.commit()

            now = now_utc()
            # Schedule that has never been run
            schedule_new = Schedule(target_id=target.id, frequency='daily')
            # Schedule that ran 12 hours ago (not due)
            schedule_not_due = Schedule(target_id=target.id + 1, frequency='daily', last_run_at=now - timedelta(hours=12))
            # Schedule that ran 25 hours ago (due)
            schedule_due = Schedule(target_id=target.id + 2, frequency='daily', last_run_at=now - timedelta(hours=25))

            # We need targets for the other schedules
            target2 = Target(value='example2.com', scan=scan)
            target3 = Target(value='example3.com', scan=scan)
            db.session.add_all([target2, target3, schedule_new, schedule_not_due, schedule_due])
            db.session.commit()

            # --- Run the service method ---
            service = SchedulerService(self.app)
            service._check_and_run_scans()

            # --- Assertions ---
            self.assertEqual(mock_launch_scan.call_count, 2)

            self.assertIsNotNone(schedule_new.last_run_at)
            self.assertIsNotNone(schedule_due.last_run_at)
            self.assertLess(schedule_not_due.last_run_at.replace(tzinfo=None), now.replace(tzinfo=None) - timedelta(hours=11))

    @freeze_time("2023-01-01 12:00:00 UTC")
    def test_is_due(self):
        """Test the _is_due helper method with freezegun."""
        service = SchedulerService(self.app)

        schedule1 = Schedule(frequency='daily', last_run_at=None)
        self.assertTrue(service._is_due(schedule1))

        schedule2 = Schedule(frequency='daily', last_run_at=datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc))
        self.assertFalse(service._is_due(schedule2))

        schedule3 = Schedule(frequency='daily', last_run_at=datetime(2022, 12, 31, 11, 0, 0, tzinfo=timezone.utc))
        self.assertTrue(service._is_due(schedule3))

        schedule4 = Schedule(frequency='weekly', last_run_at=datetime(2022, 12, 25, 13, 0, 0, tzinfo=timezone.utc))
        self.assertFalse(service._is_due(schedule4))

        schedule5 = Schedule(frequency='weekly', last_run_at=datetime(2022, 12, 24, 13, 0, 0, tzinfo=timezone.utc))
        self.assertTrue(service._is_due(schedule5))

if __name__ == '__main__':
    unittest.main()
