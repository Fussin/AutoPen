import unittest
from unittest.mock import MagicMock, patch
from cyberhunter_3d.core.triage_engine import TriageEngine
from cyberhunter_3d.core.plugins.context import ScanContext

class TestTriageEngine(unittest.TestCase):

    def setUp(self):
        self.context = MagicMock(spec=ScanContext)
        self.confidence_model_patcher = patch('cyberhunter_3d.core.triage_engine.ConfidenceModel')
        self.MockConfidenceModel = self.confidence_model_patcher.start()
        self.mock_model_instance = self.MockConfidenceModel.return_value
        self.mock_model_instance.predict.return_value = 0.85
        self.triage_engine = TriageEngine(self.context)

    def tearDown(self):
        self.confidence_model_patcher.stop()

    def test_normalization_and_deduplication(self):
        """
        Tests that raw results are normalized and deduplicated correctly.
        """
        raw_results = {
            "api_vulnerabilities": {
                "api.example.com": [
                    {
                        "template-id": "cve-2025-1234",
                        "info": {"name": "Example CVE", "severity": "high"},
                        "host": "api.example.com"
                    },
                    {
                        "template-id": "cve-2025-1234", # Same signature
                        "info": {"name": "Example CVE", "severity": "high"},
                        "host": "api.example.com"
                    }
                ],
                "api.another.com": [
                     {
                        "template-id": "xss",
                        "info": {"name": "XSS", "severity": "medium"},
                        "host": "api.another.com"
                    }
                ]
            }
        }
        self.context.get.return_value = raw_results

        findings = self.triage_engine.run()

        # Should get 2 findings: one deduplicated for api.example.com, and one for api.another.com
        self.assertEqual(len(findings), 2)

        # Find the deduplicated finding
        deduped_finding = next(f for f in findings if f['host'] == 'api.example.com')
        # It should contain evidence from both raw results
        self.assertEqual(len(deduped_finding['raw_evidence']), 2)
        # Check that confidence was set
        self.assertEqual(deduped_finding['confidence'], 0.85)

if __name__ == '__main__':
    unittest.main()
