import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.scan_manager import run_execution_phase
from cyberhunter_3d.web.models import db, Scan, Target, Asset

class TestScanManagerIntegration(unittest.TestCase):

    def setUp(self):
        # This is a simplified setup. A real test would need a test database.
        self.app = MagicMock()
        self.app.app_context.return_value.__enter__.return_value = None
        self.app.app_context.return_value.__exit__.return_value = None

    @patch('cyberhunter_3d.web.models.Asset.query', new_callable=MagicMock)
    @patch('cyberhunter_3d.web.models.Scan.query')
    @patch('cyberhunter_3d.web.models.db.session', new_callable=MagicMock)
    @patch('cyberhunter_3d.core.scan_manager.run_output_pipeline')
    @patch('cyberhunter_3d.core.scan_manager.load_config')
    @patch('cyberhunter_3d.core.scan_manager._get_results_for_scan')
    def test_run_execution_phase_triggers_output_pipeline(self, mock_get_results, mock_load_config, mock_run_output_pipeline, mock_db_session, mock_scan_query, mock_asset_query):
        # Arrange
        mock_scan = Scan(id=1, status='RUNNING')
        mock_scan.targets = [Target(value='example.com')]

        # Mock the database queries
        mock_scan_query.get.return_value = mock_scan

        mock_get_results.return_value = {'domain': 'example.com'}
        mock_load_config.return_value = {'recon_output_dir': '/tmp'}

        # Act
        run_execution_phase(1, self.app)

        # Assert
        self.assertEqual(mock_scan.status, 'COMPLETED')
        mock_run_output_pipeline.assert_called_once()

if __name__ == '__main__':
    unittest.main()
