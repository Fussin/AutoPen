import unittest
from flask import Flask
from cyberhunter_3d.web.models import db, Scan, Asset, User
from cyberhunter_3d.core.monitoring.monitor import ContinuousMonitor

class TestMonitor(unittest.TestCase):

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

    def test_compare_assets(self):
        """Test the core asset comparison logic."""
        with self.app.app_context():
            # --- Setup data within the test's context ---
            user = User(username='testuser', password_hash='123', otp_secret='secret')
            baseline_scan = Scan(user=user, status='COMPLETED')
            current_scan = Scan(user=user, status='COMPLETED')
            db.session.add_all([user, baseline_scan, current_scan])
            db.session.commit()

            baseline_scan_id = baseline_scan.id
            current_scan_id = current_scan.id

            # 1. Asset that exists in both, but changes
            db.session.add(Asset(scan_id=baseline_scan_id, type='host', value='1.1.1.1', details={'ports': [80]}))
            db.session.add(Asset(scan_id=current_scan_id, type='host', value='1.1.1.1', details={'ports': [80, 443]}))
            # 2. Asset that is removed
            db.session.add(Asset(scan_id=baseline_scan_id, type='subdomain', value='old.example.com'))
            # 3. Asset that is added
            db.session.add(Asset(scan_id=current_scan_id, type='subdomain', value='new.example.com'))
            # 4. Asset that is unchanged
            db.session.add(Asset(scan_id=baseline_scan_id, type='subdomain', value='same.example.com'))
            db.session.add(Asset(scan_id=current_scan_id, type='subdomain', value='same.example.com'))
            db.session.commit()

            # --- Run the monitor ---
            monitor = ContinuousMonitor(baseline_scan_id=baseline_scan_id, current_scan_id=current_scan_id)
            changes = monitor.compare_assets()

            # --- Assertions ---
            self.assertEqual(len(changes), 3)

            change_types = [c['details']['change'] for c in changes]
            self.assertIn('added', change_types)
            self.assertIn('removed', change_types)
            self.assertIn('modified', change_types)

            added = next(c for c in changes if c['details']['change'] == 'added')
            self.assertEqual(added['details']['value'], 'new.example.com')

            removed = next(c for c in changes if c['details']['change'] == 'removed')
            self.assertEqual(removed['details']['value'], 'old.example.com')

            modified = next(c for c in changes if c['details']['change'] == 'modified')
            self.assertEqual(modified['details']['value'], '1.1.1.1')
            self.assertEqual(modified['details']['from'], {'ports': [80]})
            self.assertEqual(modified['details']['to'], {'ports': [80, 443]})

if __name__ == '__main__':
    unittest.main()
