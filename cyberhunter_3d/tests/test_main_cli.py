import unittest
import os
import json
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from cyberhunter_3d.main import main

class TestMainCLI(unittest.TestCase):

    @patch('cyberhunter_3d.web.models.db.session')
    @patch('cyberhunter_3d.main.run_url_discovery_phase')
    @patch('cyberhunter_3d.main.get_results_dir')
    @patch('cyberhunter_3d.core.session_closure.aggregator')
    @patch('run_web.create_app')
    def test_url_discovery_cli(self, mock_create_app, mock_aggregator, mock_get_results_dir, mock_run_url_discovery_phase, mock_db_session):
        # Setup mocks
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        mock_get_results_dir.return_value = '/tmp/test_results'

        runner = CliRunner()
        result = runner.invoke(main, ['-d', 'example.com', '--url-discovery'])

        # Assertions
        self.assertEqual(result.exit_code, 0)
        mock_run_url_discovery_phase.assert_called_once()
        mock_aggregator.aggregate_results.assert_called_once()

if __name__ == '__main__':
    unittest.main()
