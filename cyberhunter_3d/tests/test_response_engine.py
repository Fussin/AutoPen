import unittest
import json
from unittest.mock import patch, MagicMock, Mock
from cyberhunter_3d.core.response_engine import ResponseEngine, JiraTicketHandler, FullReportGenerationHandler, ArchiveCreationHandler, DashboardAlertHandler, APIWebhookTriggerHandler, BugBountyPlatformSubmissionHandler, NextScanSchedulingHandler
from cyberhunter_3d.web.models import Alert, Scan, Target
from run_web import app

class TestResponseEngine(unittest.TestCase):

    def setUp(self):
        self.validated_finding = {
            "scan_id": 1,
            "target_domain": "example.com",
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

    @patch('cyberhunter_3d.core.response_engine.generate_pdf_report')
    def test_full_report_generation_handler(self, mock_generate_pdf):
        """
        Tests that the FullReportGenerationHandler calls the pdf generator.
        """
        with app.app_context():
            mock_generate_pdf.return_value = "/path/to/report.pdf"
            handler = FullReportGenerationHandler()
            result = handler.handle(self.validated_finding)

            mock_generate_pdf.assert_called_once()
            self.assertIn("/path/to/report.pdf", result)

    @patch('cyberhunter_3d.core.response_engine.get_results_dir')
    @patch('cyberhunter_3d.core.response_engine.zipfile')
    def test_archive_creation_handler(self, mock_zipfile, mock_get_results_dir):
        """
        Tests that the ArchiveCreationHandler creates a zip archive.
        """
        mock_get_results_dir.return_value = "/tmp/results"
        handler = ArchiveCreationHandler()
        result = handler.handle(self.validated_finding)

        mock_get_results_dir.assert_called_once_with("example.com", 1)
        mock_zipfile.ZipFile.assert_called_once_with("/tmp/results/scan_archive_1.zip", 'w', mock_zipfile.ZIP_DEFLATED)
        self.assertIn("Archive created at", result)

    def test_dashboard_alert_handler(self):
        """
        Tests that the DashboardAlertHandler creates an alert object.
        """
        handler = DashboardAlertHandler()
        finding = self.validated_finding.copy()
        result = handler.handle(finding)

        self.assertIn("Dashboard Alert Created", result)
        self.assertIn('alerts', finding)
        self.assertEqual(len(finding['alerts']), 1)
        self.assertIsInstance(finding['alerts'][0], Alert)
        self.assertEqual(finding['alerts'][0].message, "New finding: Test Vulnerability")

    @patch('cyberhunter_3d.core.response_engine.requests.post')
    @patch('cyberhunter_3d.core.response_engine.os.getenv')
    def test_api_webhook_trigger_handler(self, mock_getenv, mock_post):
        """
        Tests that the APIWebhookTriggerHandler sends a POST request.
        """
        mock_getenv.return_value = "http://example.com/webhook"
        handler = APIWebhookTriggerHandler()
        result = handler.handle(self.validated_finding)

        mock_getenv.assert_called_once_with("API_WEBHOOK_URL")
        mock_post.assert_called_once_with("http://example.com/webhook", json=self.validated_finding)
        self.assertEqual(result, "API Webhook Triggered")

    @patch('cyberhunter_3d.core.response_engine.get_results_dir')
    @patch('builtins.open')
    def test_bug_bounty_submission_handler(self, mock_open, mock_get_results_dir):
        """
        Tests that the BugBountyPlatformSubmissionHandler writes a file.
        """
        mock_get_results_dir.return_value = "/tmp/results"
        handler = BugBountyPlatformSubmissionHandler()
        result = handler.handle(self.validated_finding)

        mock_get_results_dir.assert_called_once_with("example.com", 1)
        mock_open.assert_called_once_with("/tmp/results/bug_bounty_submission_Test_Vulnerability.json", 'w')
        self.assertIn("Bug bounty submission created at", result)

    @patch('cyberhunter_3d.core.response_engine.db')
    def test_next_scan_scheduling_handler(self, mock_db):
        """
        Tests that the NextScanSchedulingHandler creates a new scan.
        """
        with app.app_context():
            mock_scan = Mock()
            mock_scan.user_id = 1
            mock_scan.id = 1
            mock_scan.in_scope_rules = ""
            mock_scan.out_of_scope_rules = ""
            mock_scan.targets = [Mock()]

            with patch('cyberhunter_3d.core.response_engine.Scan.query') as mock_query:
                mock_query.get.return_value = mock_scan
                handler = NextScanSchedulingHandler()
                result = handler.handle(self.validated_finding)

            self.assertEqual(mock_db.session.add.call_count, 2) # 1 for scan, 1 for target
            self.assertIn("Next scan scheduled with ID", result)

if __name__ == '__main__':
    unittest.main()
