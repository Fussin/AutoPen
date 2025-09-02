import unittest
from unittest.mock import patch, MagicMock
from run_web import create_app
from cyberhunter_3d.web.models import db, Finding
from cyberhunter_3d.scripts.retrain_models import retrain_confidence_model

from cyberhunter_3d.web.api import api_bp

class TestRetrainingPipeline(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.register_blueprint(api_bp)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    @patch('cyberhunter_3d.scripts.retrain_models.ConfidenceModel')
    def test_retraining_pipeline(self, mock_confidence_model):
        """Test that the retraining script fetches data and calls the model's train method."""
        # 1. Setup: Populate the in-memory database with labeled findings
        with self.app.app_context():
            for i in range(15): # Create 15 findings
                finding = Finding(
                    scan_id=1,
                    title=f"Finding {i}",
                    severity="Medium",
                    confidence=0.5,
                    description="...",
                    raw_evidence={},
                    finding_signature=f"test:sig:{i}",
                    validation_outcome= (i % 2 == 0) # Alternate True/False
                )
                db.session.add(finding)
            db.session.commit()

        # 2. Action: Run the retraining function
        # We need to mock create_app to return our test app
        with patch('cyberhunter_3d.scripts.retrain_models.create_app', return_value=self.app):
            retrain_confidence_model()

        # 3. Assertion: Check that the ConfidenceModel's train method was called
        mock_model_instance = mock_confidence_model.return_value
        self.assertTrue(mock_model_instance.train.called)

        # Check that it was called with the correct number of findings
        call_args, _ = mock_model_instance.train.call_args
        training_data = call_args[0]
        self.assertEqual(len(training_data), 15)

        # Check the structure of one of the data points
        self.assertIn('finding_signature', training_data[0])
        self.assertIn('validation_outcome', training_data[0])
        self.assertEqual(training_data[0]['validation_outcome'], True)
        self.assertEqual(training_data[1]['validation_outcome'], False)


if __name__ == '__main__':
    unittest.main()
