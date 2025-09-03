import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.response_engine import ResponseEngine, SlackNotificationHandler, EmailResponseHandler

class TestResponseEngine(unittest.TestCase):
    def setUp(self):
        self.test_findings = [
            {'id': 'f1', 'contextual_risk_score': 9.5, 'title': 'Critical RCE'},
            {'id': 'f2', 'contextual_risk_score': 7.0, 'title': 'Medium XSS'},
            {'id': 'f3', 'contextual_risk_score': 8.0, 'title': 'High SQLi'},
        ]
        self.test_config = {
            "response_engine": {
                "risk_threshold": 8.0,
                "enable_slack_notifications": True,
                "enable_email_notifications": True,
                "enable_jira_tickets": False,
            }
        }

    @patch('requests.post')
    def test_slack_handler(self, mock_post):
        handler = SlackNotificationHandler()
        handler.webhook_url = "https://fake.slack.url"
        handler.handle(self.test_findings[0])
        mock_post.assert_called_once()

    @patch('smtplib.SMTP')
    def test_email_handler(self, mock_smtp):
        handler = EmailResponseHandler()
        handler.smtp_server = "smtp.example.com"
        handler.recipient = "test@example.com"
        handler.handle(self.test_findings[0])
        self.assertTrue(mock_smtp.return_value.__enter__.return_value.sendmail.called)

    @patch('cyberhunter_3d.core.response_engine.SlackNotificationHandler')
    @patch('cyberhunter_3d.core.response_engine.EmailResponseHandler')
    @patch('cyberhunter_3d.core.response_engine.JiraTicketHandler')
    def test_engine_triggering(self, mock_jira_handler, mock_email_handler, mock_slack_handler):
        mock_slack_instance = mock_slack_handler.return_value
        mock_email_instance = mock_email_handler.return_value

        engine = ResponseEngine(self.test_findings, self.test_config)
        engine.run()

        self.assertEqual(mock_slack_instance.handle.call_count, 2)
        self.assertEqual(mock_email_instance.handle.call_count, 2)
        mock_jira_handler.assert_not_called()

if __name__ == '__main__':
    unittest.main()
