import unittest
from unittest.mock import patch
from cyberhunter_3d.core.validation_engine import ValidationEngine
from cyberhunter_3d.core.vulnerability.validation import XSSValidator, SQLiValidator

class TestValidationEngine(unittest.TestCase):

    @patch('cyberhunter_3d.core.vulnerability.validation.requests.get')
    def test_xss_validation_flow(self, mock_get):
        """
        Tests the validation flow for an XSS finding.
        """
        mock_response = mock_get.return_value
        mock_response.text = "<html><body><script>alert(1)</script></body></html>"

        findings = [
            {
                "title": "XSS in search query",
                "vulnerability_type": "CWE-79",
                "confidence": 0.85,
                "raw_evidence": [{
                    "template-id": "xss",
                    "matched-at": "http://test.com?q=<script>alert(1)</script>",
                    "extracted-results": ["<script>alert(1)</script>"]
                }]
            }
        ]

        engine = ValidationEngine(findings)
        results = engine.run()

        self.assertEqual(results[0]['status'], 'Validated')
        self.assertEqual(results[0]['validation_outcome'], True)
        self.assertIn('proof_of_concept', results[0])
        self.assertIn('severity_metrics', results[0])

    @patch('cyberhunter_3d.core.vulnerability.validation.requests.get')
    def test_sqli_validation_flow(self, mock_get):
        """
        Tests the validation flow for an SQLi finding.
        """
        call_count = 0
        def time_mock():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 1
            return 7

        findings = [
            {
                "title": "SQLi in user id",
                "vulnerability_type": "CWE-89",
                "confidence": 0.9,
                "raw_evidence": [{"template-id": "sqli", "matched-at": "http://test.com?id=1"}]
            }
        ]

        engine = ValidationEngine(findings, clock=time_mock)
        results = engine.run()

        self.assertEqual(results[0]['status'], 'Validated')
        self.assertEqual(results[0]['validation_outcome'], True)
        self.assertIn('proof_of_concept', results[0])
        self.assertIn('severity_metrics', results[0])

    def test_low_confidence_finding_is_skipped(self):
        """
        Tests that a finding with low confidence is skipped.
        """
        findings = [
            {
                "title": "XSS in search query",
                "vulnerability_type": "CWE-79",
                "confidence": 0.5,
                "raw_evidence": [{"template-id": "xss", "matched-at": "http://test.com?q=<script>alert(1)</script>"}]
            }
        ]

        with patch.object(XSSValidator, 'validate') as mock_validate:
            engine = ValidationEngine(findings)
            results = engine.run()

            mock_validate.assert_not_called()
            self.assertEqual(results[0]['status'], 'Validation Skipped (Low Confidence)')
            self.assertIsNone(results[0]['validation_outcome'])

if __name__ == '__main__':
    unittest.main()
