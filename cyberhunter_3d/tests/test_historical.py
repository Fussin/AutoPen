import unittest
import os
from datetime import datetime, timedelta
from flask import Flask
from cyberhunter_3d.web.models import db, User, Scan, Asset
from cyberhunter_3d.core.intelligence.historical import get_subdomain_growth, get_live_host_growth, get_new_technologies_growth

class TestHistoricalIntelligence(unittest.TestCase):

    def setUp(self):
        """Set up a temporary in-memory database for testing."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        with self.app.app_context():
            db.create_all()
            self.populate_db()

    def tearDown(self):
        """Clean up the database after tests."""
        with self.app.app_context():
            db.drop_all()

    def populate_db(self):
        """Populate the database with sample data."""
        user1 = User(id=1, username='testuser', password_hash='hash', otp_secret='secret')
        db.session.add(user1)

        # Scan 1: 2 days ago
        scan1 = Scan(id=1, user_id=1, created_at=datetime.utcnow() - timedelta(days=2))
        db.session.add(scan1)
        db.session.add_all([
            Asset(scan_id=1, type='subdomain', value='a.example.com'),
            Asset(scan_id=1, type='subdomain', value='b.example.com'),
            Asset(scan_id=1, type='live_host', value='a.example.com'),
            Asset(scan_id=1, type='technology', value='nginx'),
        ])

        # Scan 2: 1 day ago
        scan2 = Scan(id=2, user_id=1, created_at=datetime.utcnow() - timedelta(days=1))
        db.session.add(scan2)
        db.session.add_all([
            Asset(scan_id=2, type='subdomain', value='c.example.com'),
            Asset(scan_id=2, type='live_host', value='c.example.com'),
            Asset(scan_id=2, type='technology', value='apache'),
            Asset(scan_id=2, type='technology', value='react'),
        ])

        db.session.commit()

    def test_get_subdomain_growth(self):
        """Test aggregation of subdomain growth data."""
        with self.app.app_context():
            data = get_subdomain_growth(1)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]['count'], 2) # 2 subdomains in first scan
            self.assertEqual(data[1]['count'], 1) # 1 subdomain in second scan

    def test_get_live_host_growth(self):
        """Test aggregation of live host growth data."""
        with self.app.app_context():
            data = get_live_host_growth(1)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]['count'], 1)
            self.assertEqual(data[1]['count'], 1)

    def test_get_new_technologies_growth(self):
        """Test aggregation of new technology growth data."""
        with self.app.app_context():
            data = get_new_technologies_growth(1)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]['count'], 1)
            self.assertEqual(data[1]['count'], 2)

if __name__ == '__main__':
    unittest.main()
