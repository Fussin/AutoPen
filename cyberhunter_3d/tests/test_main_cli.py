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
    @patch('cyberhunter_3d.main.aggregate_results')
    @patch('run_web.create_app')
    def test_url_discovery_cli(self, mock_create_app, mock_aggregate_results, mock_get_results_dir, mock_run_url_discovery_phase, mock_db_session):
        # Setup mocks
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        mock_get_results_dir.return_value = '/tmp/test_results'

        runner = CliRunner()
        result = runner.invoke(main, ['-d', 'example.com', '--url-discovery'])

        # Assertions
        self.assertEqual(result.exit_code, 0)
        mock_run_url_discovery_phase.assert_called_once()
        mock_aggregate_results.assert_called_once()

    @patch('cyberhunter_3d.web.models.db.session')
    @patch('cyberhunter_3d.main.enumerate_subdomains_v2')
    @patch('cyberhunter_3d.main.run_url_discovery_phase')
    @patch('cyberhunter_3d.main.run_network_scan_phase')
    @patch('cyberhunter_3d.main.run_vulnerability_scan_phase')
    @patch('cyberhunter_3d.main.get_results_dir')
    @patch('cyberhunter_3d.main.aggregate_results')
    @patch('run_web.create_app')
    def test_parallel_execution_cli(self, mock_create_app, mock_aggregate_results, mock_get_results_dir,
                                     mock_run_vulnerability_scan_phase, mock_run_network_scan_phase,
                                     mock_run_url_discovery_phase, mock_enumerate_subdomains_v2, mock_db_session):
        # Setup mocks
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        mock_get_results_dir.return_value = '/tmp/test_results'
        # Ensure enumerate_subdomains_v2 returns a non-empty path to proceed
        mock_enumerate_subdomains_v2.return_value = ({'master_results_list': '/tmp/results.json'}, None, None)

        runner = CliRunner()
        result = runner.invoke(main, ['-d', 'example.com'])

        # Assertions
        self.assertEqual(result.exit_code, 0)
        mock_enumerate_subdomains_v2.assert_called_once()
        mock_run_url_discovery_phase.assert_called_once()
        mock_run_network_scan_phase.assert_called_once()
        mock_run_vulnerability_scan_phase.assert_called_once()
        mock_aggregate_results.assert_called_once()

if __name__ == '__main__':
    unittest.main()
