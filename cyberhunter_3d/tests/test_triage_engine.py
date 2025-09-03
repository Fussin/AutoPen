import unittest
from unittest.mock import MagicMock, patch
from run_web import create_app
from cyberhunter_3d.web.models import db
from cyberhunter_3d.core.triage_engine import TriageEngine
from cyberhunter_3d.core.plugins.context import ScanContext

class TestTriageEngine(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.context = MagicMock(spec=ScanContext)
        self.context.get.side_effect = lambda key, default=None: self._context_data.get(key, default)
        self.scan_id = 1
        self._context_data = {"scan_id": self.scan_id}

        self.confidence_model_patcher = patch('cyberhunter_3d.core.triage_engine.ConfidenceModel')
        self.MockConfidenceModel = self.confidence_model_patcher.start()
        self.mock_model_instance = self.MockConfidenceModel.return_value
        self.mock_model_instance.predict.return_value = 0.85

        self.intelligent_engine_patcher = patch('cyberhunter_3d.core.triage_engine.IntelligentEngine')
        self.MockIntelligentEngine = self.intelligent_engine_patcher.start()

        def mock_engine_constructor(findings):
            mock_engine_instance = MagicMock()
            mock_engine_instance.run.return_value = findings
            return mock_engine_instance

        self.MockIntelligentEngine.side_effect = mock_engine_constructor

        self.triage_engine = TriageEngine(self.context)

    def tearDown(self):
        self.confidence_model_patcher.stop()
        self.intelligent_engine_patcher.stop()
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_normalization_and_saving(self):
        raw_results = {
            "api_vulnerabilities": {
                "api.example.com": [{"template-id": "cve-2025-1234", "info": {"name": "Example CVE", "severity": "high"}}]
            }
        }
        self._context_data["specialized_scan_results"] = raw_results

        findings = self.triage_engine.run()

        self.assertEqual(len(findings), 1)
        self.MockIntelligentEngine.assert_called_once()

if __name__ == '__main__':
    unittest.main()
