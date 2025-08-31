import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.validation_engine import ValidationEngine, TimeBasedSQLiHandler, ApiKeyValidationHandler

class TestValidationEngine(unittest.TestCase):

    def test_validation_engine_instantiation(self):
        # Arrange
        findings = [
            {"title": "Test Finding", "severity": "High", "confidence": "High"}
        ]

        # Act
        engine = ValidationEngine(findings)

        # Assert
        self.assertIsNotNone(engine)
        self.assertEqual(len(engine.findings_to_validate), 1)

    @patch('time.time')
    @patch('requests.get')
    def test_time_based_sqli_handler_valid(self, mock_get, mock_time):
        # Arrange
        handler = TimeBasedSQLiHandler()
        finding = {
            "title": "SQL Injection",
            "supporting_evidence": [{"host": "http://test.com"}]
        }
        # Simulate a response that takes longer than the delay
        mock_time.side_effect = [0, 6, 7, 8, 9, 10]

        # Act
        is_validated = handler.validate(finding)

        # Assert
        self.assertTrue(is_validated)

    @patch('requests.get')
    def test_api_key_validation_handler_valid(self, mock_get):
        # Arrange
        handler = ApiKeyValidationHandler()
        finding = {
            "title": "Leaked API Key",
            "supporting_evidence": [{
                "leaked_key_finding": {
                    "Raw": "var api_key = 'supersecretkey'",
                    "Source": "http://test.com/script.js"
                }
            }]
        }
        # Simulate a successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Act
        is_validated = handler.validate(finding)

        # Assert
        self.assertTrue(is_validated)

if __name__ == '__main__':
    unittest.main()
