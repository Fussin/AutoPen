import unittest
import json
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.response_engine import ResponseEngine, JiraTicketHandler, SlackAlertingHandler

class TestResponseEngine(unittest.TestCase):

    def setUp(self):
        self.validated_finding = {
            "id": "vuln-123",
            "title": "Test Vulnerability",
            "severity": "High",
            "description": "This is a test description.",
            "confidence": "High",
            "host": "example.com",
            "vulnerability_type": "CWE-89",
            "raw_evidence": [{"data": "some evidence"}],
            "tags": ["SQLi", "nuclei"],
            "status": "Validated"
        }
        self.unvalidated_finding = {
            "id": "vuln-456",
            "title": "Unvalidated Finding",
            "status": "Validation Failed"
        }

    @patch.object(JiraTicketHandler, 'handle')
    @patch.object(SlackAlertingHandler, 'handle')
    def test_engine_only_handles_validated_findings(self, mock_slack_handle, mock_jira_handle):
        """
        Tests that the engine's run method only calls handlers for findings
        with a 'Validated' status.
        """
        findings = [self.validated_finding, self.unvalidated_finding]
        engine = ResponseEngine(findings)
        engine.run()

        mock_jira_handle.assert_called_once_with(self.validated_finding)
        mock_slack_handle.assert_called_once_with(self.validated_finding)

    @patch('cyberhunter_3d.core.response_engine.JIRA')
    def test_jira_handler_constructs_correct_payload(self, MockJira):
        """
        Tests that the JiraTicketHandler creates a correctly formatted issue dict.
        """
        # Mock the JIRA client instance
        mock_jira_client = MagicMock()
        MockJira.return_value = mock_jira_client

        # Setup handler with mocked env vars
        with patch.dict('os.environ', {
            'JIRA_URL': 'https://test.jira.com',
            'JIRA_USERNAME': 'user',
            'JIRA_API_TOKEN': 'token',
            'JIRA_PROJECT_KEY': 'SEC'
        }):
            handler = JiraTicketHandler()
            handler.handle(self.validated_finding)

            # Assert that create_issue was called
            mock_jira_client.create_issue.assert_called_once()

            # Assert the content of the issue dictionary
            call_args = mock_jira_client.create_issue.call_args[1]
            issue_fields = call_args['fields']

            self.assertEqual(issue_fields['project']['key'], 'SEC')
            self.assertIn("Test Vulnerability", issue_fields['summary'])
            self.assertIn("Severity:* High", issue_fields['description'])
            self.assertIn("Host:* example.com", issue_fields['description'])
            self.assertIn(json.dumps(self.validated_finding['raw_evidence'], indent=2), issue_fields['description'])

    @patch('cyberhunter_3d.core.response_engine.requests.post')
    def test_slack_handler_constructs_correct_payload(self, mock_post):
        """
        Tests that the SlackAlertingHandler sends a correctly formatted JSON payload.
        """
        # Setup handler with mocked env var
        with patch.dict('os.environ', {'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/services/FAKE'}):
            handler = SlackAlertingHandler()
            handler.handle(self.validated_finding)

            # Assert that requests.post was called
            mock_post.assert_called_once()

            # Assert the content of the Slack message
            call_args = mock_post.call_args[1]
            slack_payload = call_args['json']
            main_block_text = slack_payload['attachments'][0]['blocks'][2]['fields']

            self.assertIn("Test Vulnerability", slack_payload['attachments'][0]['blocks'][1]['text']['text'])
            self.assertIn("Severity:*\nHigh", main_block_text[0]['text'])
            self.assertIn("Host:*\nexample.com", main_block_text[1]['text'])

if __name__ == '__main__':
    unittest.main()
