import unittest
from unittest.mock import patch, MagicMock
from run_web import create_app
from cyberhunter_3d.web.models import db, Finding
from cyberhunter_3d.scripts.retrain_models import retrain_confidence_model

class TestRetrainingPipeline(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch('cyberhunter_3d.scripts.retrain_models.ConfidenceModel')
    def test_retraining_pipeline(self, mock_confidence_model):
        with self.app.app_context():
            for i in range(15):
                finding = Finding(scan_id=1, title=f"F{i}", severity="M", confidence=0.5, description="d", raw_evidence={}, finding_signature=f"s:{i}", validation_outcome=(i % 2 == 0))
                db.session.add(finding)
            db.session.commit()

        with patch('cyberhunter_3d.scripts.retrain_models.create_app', return_value=self.app):
            retrain_confidence_model()

        mock_model_instance = mock_confidence_model.return_value
        self.assertTrue(mock_model_instance.train.called)

        call_args, _ = mock_model_instance.train.call_args
        self.assertEqual(len(call_args[0]), 15)

if __name__ == '__main__':
    unittest.main()
