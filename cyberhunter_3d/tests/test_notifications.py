import unittest
from unittest.mock import MagicMock, patch
from cyberhunter_3d.core.response_engine import ResponseEngine
from cyberhunter_3d.core.notifications.notification_manager import NotificationManager

class TestNotificationResponseHandlers(unittest.TestCase):

    @patch('cyberhunter_3d.core.response_engine.NotificationManager')
    def test_notification_handlers_are_called(self, MockNotificationManager):
        """
        Verify that notification handlers in the ResponseEngine use the NotificationManager.
        """
        mock_manager_instance = MockNotificationManager.return_value

        # Simulate a validated finding
        validated_finding = {
            "title": "Validated Test Finding",
            "severity": "High",
            "status": "Validated",
            "host": "validated.example.com",
            "description": "A validated test finding."
        }

        # Simulate a critical validated finding
        critical_finding = {
            "title": "Critical Test Finding",
            "severity": "Critical",
            "status": "Validated",
            "host": "critical.example.com",
            "description": "A critical test finding."
        }

        findings = [validated_finding, critical_finding]

        # We patch the non-notification handlers to isolate our test
        with patch('cyberhunter_3d.core.response_engine.JiraTicketHandler') as mock_jira, \
             patch('cyberhunter_3d.core.response_engine.DashboardAlertHandler') as mock_dashboard, \
             patch('cyberhunter_3d.core.response_engine.APIWebhookTriggerHandler') as mock_webhook, \
             patch('cyberhunter_3d.core.response_engine.FullReportGenerationHandler') as mock_report, \
             patch('cyberhunter_3d.core.response_engine.BugBountyPlatformSubmissionHandler') as mock_bounty, \
             patch('cyberhunter_3d.core.response_engine.ArchiveCreationHandler') as mock_archive, \
             patch('cyberhunter_3d.core.response_engine.NextScanSchedulingHandler') as mock_schedule:

            # Set return values for the mocked handlers
            mock_jira.return_value.handle.return_value = None
            mock_dashboard.return_value.handle.return_value = None
            mock_webhook.return_value.handle.return_value = None
            mock_report.return_value.handle.return_value = None
            mock_bounty.return_value.handle.return_value = None
            mock_archive.return_value.handle.return_value = None
            mock_schedule.return_value.handle.return_value = None

            response_engine = ResponseEngine(findings)
            response_engine.run()

        # Check call counts
        # Slack and Email should be called for both findings
        # SMS should only be called for the critical one
        self.assertEqual(mock_manager_instance.send_notification.call_count, 5)

        # Extract calls for easier assertion
        calls = mock_manager_instance.send_notification.call_args_list

        # Slack calls
        slack_calls = [c for c in calls if c.args[0] == 'slack']
        self.assertEqual(len(slack_calls), 2)

        # Email calls
        email_calls = [c for c in calls if c.args[0] == 'email']
        self.assertEqual(len(email_calls), 2)

        # SMS calls
        sms_calls = [c for c in calls if c.args[0] == 'sms']
        self.assertEqual(len(sms_calls), 1)

        # Verify the SMS call was for the critical finding
        self.assertIn("Critical Security Finding", sms_calls[0].args[1])
        self.assertIn("critical.example.com", sms_calls[0].args[1])

if __name__ == '__main__':
    unittest.main()
