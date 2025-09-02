import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from cyberhunter_3d.main import cli
from cyberhunter_3d.web.models import Target

class TestMainCLI(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch('cyberhunter_3d.main.run_url_discovery_phase')
    @patch('cyberhunter_3d.main.get_results_dir')
    @patch('cyberhunter_3d.main.aggregate_results')
    @patch('run_web.create_app')
    @patch('cyberhunter_3d.web.models.db.session')
    def test_scan_command_url_discovery(self, mock_session, mock_create_app, mock_aggregate_results, mock_get_results_dir, mock_run_url_discovery_phase):
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        mock_context = MagicMock()
        mock_context.__enter__.return_value = None
        mock_context.__exit__.return_value = None
        mock_app.app_context.return_value = mock_context

        mock_get_results_dir.return_value = '/tmp/test_results'

        result = self.runner.invoke(cli, ['scan', '-d', 'example.com', '--url-discovery'])

        self.assertEqual(result.exit_code, 0, result.output)
        mock_run_url_discovery_phase.assert_called_once()
        mock_aggregate_results.assert_called_once()
        self.assertTrue(mock_session.commit.called)

    @patch('run_web.create_app')
    @patch('cyberhunter_3d.web.models.db.session')
    def test_monitor_command_enable(self, mock_session, mock_create_app):
        mock_app = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = None
        mock_context.__exit__.return_value = None
        mock_app.app_context.return_value = mock_context
        mock_create_app.return_value = mock_app

        mock_target = Target(value='example.com', is_monitoring_enabled=False)

        with patch('cyberhunter_3d.web.models.Target.query') as mock_query:
            mock_query.filter_by.return_value.first.return_value = mock_target

            result = self.runner.invoke(cli, ['monitor', '--target', 'example.com', '--enable'])

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(mock_target.is_monitoring_enabled)
            self.assertIn("Successfully enabled monitoring", result.output)
            self.assertTrue(mock_session.commit.called)

    @patch('run_web.create_app')
    @patch('cyberhunter_3d.web.models.db.session')
    def test_monitor_command_disable(self, mock_session, mock_create_app):
        mock_app = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = None
        mock_context.__exit__.return_value = None
        mock_app.app_context.return_value = mock_context
        mock_create_app.return_value = mock_app

        mock_target = Target(value='example.com', is_monitoring_enabled=True)

        with patch('cyberhunter_3d.web.models.Target.query') as mock_query:
            mock_query.filter_by.return_value.first.return_value = mock_target

            result = self.runner.invoke(cli, ['monitor', '--target', 'example.com', '--disable'])

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertFalse(mock_target.is_monitoring_enabled)
            self.assertIn("Successfully disabled monitoring", result.output)
            self.assertTrue(mock_session.commit.called)

if __name__ == '__main__':
    unittest.main()
