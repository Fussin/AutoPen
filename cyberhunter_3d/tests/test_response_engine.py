import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.response_engine import ResponseEngine, SlackNotificationHandler, EmailResponseHandler

class TestResponseEngine(unittest.TestCase):
    def setUp(self):
        self.test_findings = [
            {'id': 'finding-1', 'contextual_risk_score': 9.5, 'vulnerability_name': 'Critical RCE'},
            {'id': 'finding-2', 'contextual_risk_score': 7.0, 'vulnerability_name': 'Medium XSS'},
            {'id': 'finding-3', 'contextual_risk_score': 8.0, 'vulnerability_name': 'High SQLi'},
        ]
        self.test_config = {
            "response_engine": {
                "risk_threshold": 8.0,
                "enable_slack_notifications": True,
                "enable_email_notifications": True,
                "enable_jira_tickets": False, # Ensure this is off for these tests
            }
        }

    @patch('requests.post')
    def test_slack_notification_handler(self, mock_post):
        """Test that the Slack handler sends the correct data."""
        handler = SlackNotificationHandler()
        handler.webhook_url = "https://hooks.slack.com/services/FAKE/URL"
        handler.handle(self.test_findings[0])

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("Critical RCE", kwargs['json']['text'])

    @patch('smtplib.SMTP')
    def test_email_response_handler(self, mock_smtp):
        """Test that the Email handler sends the correct email."""
        handler = EmailResponseHandler()
        handler.smtp_server = "smtp.example.com"
        handler.smtp_port = 587
        handler.smtp_user = "user"
        handler.smtp_pass = "pass"
        handler.recipient = "test@example.com"

        handler.handle(self.test_findings[0])

        instance = mock_smtp.return_value.__enter__.return_value
        self.assertTrue(instance.starttls.called)
        self.assertTrue(instance.login.called)
        self.assertTrue(instance.sendmail.called)

        args, _ = instance.sendmail.call_args
        self.assertIn("Subject: High-Risk Security Finding: Critical RCE", args[2])

    @patch('cyberhunter_3d.core.response_engine.SlackNotificationHandler')
    @patch('cyberhunter_3d.core.response_engine.EmailResponseHandler')
    @patch('cyberhunter_3d.core.response_engine.JiraTicketHandler')
    def test_response_engine_triggering(self, mock_jira_handler, mock_email_handler, mock_slack_handler):
        """Test that the engine triggers handlers for findings above the threshold."""
        mock_slack_instance = mock_slack_handler.return_value
        mock_email_instance = mock_email_handler.return_value

        engine = ResponseEngine(self.test_findings, self.test_config)
        engine.run()

        # Should be called for finding-1 (9.5) and finding-3 (8.0)
        self.assertEqual(mock_slack_instance.handle.call_count, 2)
        self.assertEqual(mock_email_instance.handle.call_count, 2)

        # Check that it was called with the correct findings
        self.assertEqual(mock_slack_instance.handle.call_args_list[0].args[0]['id'], 'finding-1')
        self.assertEqual(mock_slack_instance.handle.call_args_list[1].args[0]['id'], 'finding-3')

        # Jira handler should not be called
        self.assertEqual(mock_jira_handler.return_value.handle.call_count, 0)

if __name__ == '__main__':
    unittest.main()
