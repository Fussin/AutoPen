import unittest
import json
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.response_engine import ResponseEngine, JiraTicketHandler

class TestResponseEngine(unittest.TestCase):

    def setUp(self):
        self.validated_finding = {
            "title": "Test Vulnerability", "status": "Validated",
            "disposition": None
        }
        self.unvalidated_finding = {"title": "Unvalidated", "status": "New"}

    @patch.object(JiraTicketHandler, 'handle', return_value="Ticket-123")
    def test_engine_updates_disposition(self, mock_jira_handle):
        """
        Tests that the engine correctly updates the disposition field after a
        handler takes action.
        """
        findings = [self.validated_finding, self.unvalidated_finding]
        engine = ResponseEngine(findings)
        results = engine.run()

        # Handler should only be called for the validated finding
        mock_jira_handle.assert_called_once_with(self.validated_finding)

        # Check that the disposition was updated correctly
        self.assertEqual(results[0]['disposition'], "Ticket-123")
        # Check that the unvalidated finding was not modified
        self.assertIsNone(results[1].get('disposition'))

if __name__ == '__main__':
    unittest.main()
