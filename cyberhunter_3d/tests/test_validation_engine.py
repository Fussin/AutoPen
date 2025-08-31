import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.validation_engine import ValidationEngine, TimeBasedSQLiHandler, AWSKeyValidationHandler

class TestValidationEngine(unittest.TestCase):

    def test_engine_dispatches_to_correct_handler(self):
        """
        Tests that the engine correctly calls the handler based on vulnerability_type.
        """
        findings = [
            {
                "vulnerability_type": "CWE-89", # SQLi
                "confidence": "High",
                "raw_evidence": [{"template-id": "some-sqli-template"}]
            }
        ]

        with patch.object(TimeBasedSQLiHandler, 'validate', return_value=True) as mock_validate:
            engine = ValidationEngine(findings)
            validated = engine.run()

            mock_validate.assert_called_once()
            self.assertEqual(len(validated), 1)
            self.assertEqual(validated[0]['status'], 'Validated')

    @patch('cyberhunter_3d.core.validation_engine.requests.get')
    def test_time_based_sqli_handler_success(self, mock_requests_get):
        """
        Tests the TimeBasedSQLiHandler's logic for a successful validation.
        """
        # 1. Setup
        # Simulate a slow response after the payload is sent
        def side_effect(*args, **kwargs):
            time_slept = kwargs.get('timeout', 0) - 3 # timeout is delay + 3
            import time
            time.sleep(time_slept)
            return MagicMock(status_code=200)

        mock_requests_get.side_effect = side_effect

        handler = TimeBasedSQLiHandler()
        finding = {
            "confidence": "High",
            "raw_evidence": [{
                "template-id": "sqli-timing",
                "matched-at": "http://example.com/items?id=1"
            }]
        }

        # 2. Execute
        is_validated = handler.validate(finding)

        # 3. Assert
        self.assertTrue(is_validated)
        mock_requests_get.assert_called_once()
        # Check if the payload is in the called URL
        self.assertIn("SLEEP(5)", mock_requests_get.call_args[0][0])

    def test_aws_key_handler_cannot_validate_without_secret(self):
        """
        Tests that the AWSKeyValidationHandler correctly identifies it cannot
        validate an access key without a secret key.
        """
        handler = AWSKeyValidationHandler()
        finding = {
            "confidence": "High",
            "raw_evidence": [{
                "SourceMetadata": {}, # Indicates trufflehog
                "Raw": "AKIAIOSFODNN7EXAMPLE" # Example AWS Access Key
            }]
        }

        is_validated = handler.validate(finding)

        self.assertFalse(is_validated)

    def test_engine_skips_low_confidence_findings(self):
        """
        Tests that the engine does not attempt to validate findings that
        are not marked with 'High' confidence.
        """
        findings = [
            {
                "vulnerability_type": "CWE-89",
                "confidence": "Medium", # Not high confidence
                "raw_evidence": [{"template-id": "some-sqli-template"}]
            }
        ]

        with patch.object(TimeBasedSQLiHandler, 'validate') as mock_validate:
            engine = ValidationEngine(findings)
            results = engine.run()

            mock_validate.assert_not_called()
            self.assertEqual(results[0]['status'], 'Validation Skipped (Low Confidence)')

if __name__ == '__main__':
    unittest.main()
