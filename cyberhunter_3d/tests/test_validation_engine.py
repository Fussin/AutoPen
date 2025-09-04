import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.validation_engine import ValidationEngine, TimeBasedSQLiHandler

class TestValidationEngine(unittest.TestCase):

    def test_engine_updates_finding_status(self):
        """
        Tests that the engine correctly updates the status and validation_outcome
        fields of the findings it processes.
        """
        findings = [
            # This one should be validated
            {
                "vulnerability_type": "CWE-89", "confidence": 0.9,
                "raw_evidence": [{"template-id": "sqli", "matched-at": "http://a.com?p=1"}]
            },
            # This one should fail validation
            {
                "vulnerability_type": "CWE-89", "confidence": 0.8,
                "raw_evidence": [{"template-id": "sqli", "matched-at": "http://b.com?p=1"}]
            },
            # This one should be skipped
            {"vulnerability_type": "CWE-89", "confidence": 0.1}
        ]

        # Mock the handler's validate method to control the outcome
        with patch.object(TimeBasedSQLiHandler, 'validate', side_effect=[True, False]) as mock_validate:
            engine = ValidationEngine(findings)
            results = engine.run()

            self.assertEqual(mock_validate.call_count, 2)
            self.assertEqual(results[0]['status'], 'Validated')
            self.assertEqual(results[0]['validation_outcome'], True)
            self.assertEqual(results[1]['status'], 'Validation Failed')
            self.assertEqual(results[1]['validation_outcome'], False)
            self.assertEqual(results[2]['status'], 'Validation Skipped (Low Confidence)')
            self.assertIsNone(results[2]['validation_outcome'])

if __name__ == '__main__':
    unittest.main()
