import unittest
from unittest.mock import patch
from cyberhunter_3d.core.validation_engine import ValidationEngine
from cyberhunter_3d.core.vulnerability.validation import XSSValidator, SQLiValidator

class TestValidationEngine(unittest.TestCase):

    @patch('cyberhunter_3d.core.vulnerability.validation.sync_playwright')
    def test_xss_validation_flow_with_dialog(self, mock_sync_playwright):
        """
        Tests the XSS validation flow where a dialog is triggered.
        """
        # Mock Playwright to simulate a dialog event
        mock_page = mock_sync_playwright.return_value.__enter__.return_value.chromium.launch.return_value.new_page.return_value
        mock_dialog = unittest.mock.MagicMock()
        def side_effect(event, callback):
            if event == "dialog":
                callback(mock_dialog)
        mock_page.on.side_effect = side_effect

        findings = [
            {
                "title": "XSS in search query",
                "vulnerability_type": "CWE-79",
                "confidence": 0.85,
                "raw_evidence": [{"template-id": "xss", "matched-at": "http://test.com?q=<script>alert(1)</script>"}]
            }
        ]

        engine = ValidationEngine(findings)
        results = engine.run()

        self.assertEqual(results[0]['status'], 'Validated')
        self.assertEqual(results[0]['validation_outcome'], True)
        self.assertEqual(results[0]['severity_metrics']['cvss_score'], 7.5)

    @patch('cyberhunter_3d.core.vulnerability.validation.sync_playwright')
    def test_xss_validation_flow_no_dialog(self, mock_sync_playwright):
        """
        Tests the XSS validation flow where no dialog is triggered.
        """
        # Mock Playwright to simulate no dialog event
        mock_page = mock_sync_playwright.return_value.__enter__.return_value.chromium.launch.return_value.new_page.return_value
        mock_page.on.side_effect = None

        findings = [
            {
                "title": "XSS in search query",
                "vulnerability_type": "CWE-79",
                "confidence": 0.85,
                "raw_evidence": [{"template-id": "xss", "matched-at": "http://test.com?q=test"}]
            }
        ]

        # In this test, multi_tool_verification will return False, so the overall validation will fail.
        engine = ValidationEngine(findings)
        results = engine.run()

        self.assertEqual(results[0]['status'], 'Validation Failed')
        self.assertEqual(results[0]['validation_outcome'], False)

    @patch.object(SQLiValidator, '_attempt_data_extraction', return_value=True)
    def test_sqli_validation_with_data_extraction(self, mock_attempt_data_extraction):
        """
        Tests SQLi validation succeeds with data extraction.
        """
        findings = [
            {
                "title": "SQLi in user id",
                "vulnerability_type": "CWE-89",
                "confidence": 0.9,
                "raw_evidence": [{"template-id": "sqli", "matched-at": "http://test.com?id=1"}]
            }
        ]

        engine = ValidationEngine(findings)
        results = engine.run()

        self.assertEqual(results[0]['status'], 'Validated')
        self.assertEqual(results[0]['validation_outcome'], True)
        self.assertEqual(results[0]['severity_metrics']['cvss_score'], 9.8)

    @patch.object(SQLiValidator, '_attempt_data_extraction', return_value=False)
    @patch.object(SQLiValidator, '_attempt_time_based_check', return_value=True)
    def test_sqli_validation_with_time_based(self, mock_time_based, mock_data_extraction):
        """
        Tests SQLi validation succeeds with time-based check when data extraction fails.
        """
        findings = [
            {
                "title": "SQLi in user id",
                "vulnerability_type": "CWE-89",
                "confidence": 0.9,
                "raw_evidence": [{"template-id": "sqli", "matched-at": "http://test.com?id=1"}]
            }
        ]

        engine = ValidationEngine(findings)
        results = engine.run()

        self.assertEqual(results[0]['status'], 'Validated')
        self.assertEqual(results[0]['validation_outcome'], True)
        self.assertEqual(results[0]['severity_metrics']['cvss_score'], 8.8)

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
