import unittest
import json
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.response_engine import EventEngine, JiraTicketHandler, LogAlertHandler

class TestEventEngine(unittest.TestCase):

    def setUp(self):
        self.validated_finding = {
            "title": "Test Vulnerability", "status": "Validated", "type": "finding",
            "disposition": None
        }
        self.unvalidated_finding = {"title": "Unvalidated", "status": "New", "type": "finding"}
        self.test_alert = {
            "title": "New Asset Discovered", "type": "alert", "description": "A new thing was found"
        }

    @patch.object(JiraTicketHandler, 'handle', return_value="Ticket-123")
    @patch.object(LogAlertHandler, 'handle', return_value=None)
    def test_engine_handles_findings(self, mock_log_handle, mock_jira_handle):
        """
        Tests that the engine correctly handles 'finding' events and updates disposition.
        """
        events = [self.validated_finding, self.unvalidated_finding]
        engine = EventEngine(events)
        results = engine.run()

        mock_jira_handle.assert_called_once_with(self.validated_finding)
        self.assertEqual(results[0]['disposition'], "Ticket-123")
        self.assertIsNone(results[1].get('disposition'))

    @patch.object(LogAlertHandler, 'handle', return_value="Logged")
    @patch.object(JiraTicketHandler, 'handle', return_value=None)
    def test_engine_handles_alerts(self, mock_jira_handle, mock_log_handle):
        """
        Tests that the engine correctly handles 'alert' events.
        """
        events = [self.test_alert]
        engine = EventEngine(events)
        results = engine.run()

        mock_log_handle.assert_called_once_with(self.test_alert)
        self.assertEqual(results[0]['disposition'], "Logged")

if __name__ == '__main__':
    unittest.main()
