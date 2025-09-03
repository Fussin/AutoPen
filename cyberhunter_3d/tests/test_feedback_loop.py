import unittest
import json
from run_web import create_app
from cyberhunter_3d.web.models import db, User, Scan, Finding
from cyberhunter_3d.web.api import api_bp

class TestFeedbackLoop(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.register_blueprint(api_bp)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            test_user = User(username='testuser', password_hash='hash', otp_secret='secret')
            db.session.add(test_user)
            db.session.commit()
            self.api_key = test_user.api_key

            test_scan = Scan(user_id=test_user.id)
            db.session.add(test_scan)
            db.session.commit()
            self.scan_id = test_scan.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_submit_feedback_api(self):
        with self.app.app_context():
            test_finding = Finding(scan_id=self.scan_id, title="Test", severity="High", confidence=0.8, description="", raw_evidence={}, finding_signature="test:sig:1")
            db.session.add(test_finding)
            db.session.commit()
            finding_id = test_finding.id

        feedback_data = {'validation_outcome': True, 'disposition': 'true_positive'}
        response = self.client.post(
            f'/api/v1/findings/{finding_id}/feedback',
            headers={'X-API-Key': self.api_key},
            data=json.dumps(feedback_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            updated_finding = Finding.query.get(finding_id)
            self.assertEqual(updated_finding.validation_outcome, True)

if __name__ == '__main__':
    unittest.main()
