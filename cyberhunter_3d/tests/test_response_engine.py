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

    @patch('cyberhunter_3d.core.response_engine.NextScanSchedulingHandler')
    @patch('cyberhunter_3d.core.response_engine.ArchiveCreationHandler')
    @patch('cyberhunter_3d.core.response_engine.BugBountyPlatformSubmissionHandler')
    @patch('cyberhunter_3d.core.response_engine.FullReportGenerationHandler')
    @patch('cyberhunter_3d.core.response_engine.APIWebhookTriggerHandler')
    @patch('cyberhunter_3d.core.response_engine.DashboardAlertHandler')
    @patch('cyberhunter_3d.core.response_engine.SMSAlertHandler')
    @patch('cyberhunter_3d.core.response_engine.EmailAlertHandler')
    @patch('cyberhunter_3d.core.response_engine.SlackNotificationHandler')
    @patch('cyberhunter_3d.core.response_engine.JiraTicketHandler')
    def test_engine_updates_disposition(self, mock_jira, mock_slack, mock_email, mock_sms, mock_dashboard, mock_webhook, mock_report, mock_bounty, mock_archive, mock_schedule):
        """
        Tests that the engine correctly updates the disposition field after a
        handler takes action.
        """
        # Configure mocks
        mock_jira.return_value.handle.return_value = "Ticket-123"
        mock_slack.return_value.handle.return_value = None
        mock_email.return_value.handle.return_value = None
        mock_sms.return_value.handle.return_value = None
        mock_dashboard.return_value.handle.return_value = None
        mock_webhook.return_value.handle.return_value = None
        mock_report.return_value.handle.return_value = None
        mock_bounty.return_value.handle.return_value = None
        mock_archive.return_value.handle.return_value = None
        mock_schedule.return_value.handle.return_value = None

        findings = [self.validated_finding, self.unvalidated_finding]
        engine = ResponseEngine(findings)
        results = engine.run()

        # Jira handler should only be called for the validated finding
        mock_jira.return_value.handle.assert_called_once_with(self.validated_finding)

        # Check that the disposition was updated correctly
        self.assertEqual(results[0]['disposition'], "Ticket-123")
        # Check that the unvalidated finding was not modified
        self.assertIsNone(results[1].get('disposition'))

if __name__ == '__main__':
    unittest.main()
