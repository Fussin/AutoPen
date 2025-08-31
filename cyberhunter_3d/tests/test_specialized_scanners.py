import unittest
from unittest.mock import patch, MagicMock
import json
import tempfile
import shutil
from cyberhunter_3d.core.plugins.impl.wordpress_scanner import WordPressScannerPlugin
from cyberhunter_3d.core.plugins.impl.api_security_scanner import ApiSecurityScannerPlugin
from cyberhunter_3d.core.specialized_scan_manager import SpecializedScanManager
from cyberhunter_3d.core.plugins.context import ScanContext

class TestSpecializedScanners(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.context = ScanContext(target_domain="example.com", scan_id="test_scan")
        self.context.results_dir = self.test_dir

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('cyberhunter_3d.core.plugins.impl.wordpress_scanner.load_config')
    @patch('cyberhunter_3d.core.plugins.impl.wordpress_scanner.WordPressScannerPlugin._run_command')
    def test_wordpress_scanner_plugin(self, mock_run_command, mock_load_config):
        # Arrange
        mock_load_config.return_value = {
            "tool_commands": {
                "wpscan_scan": "wpscan --url {target_url} --api-token {api_token} -f json"
            }
        }
        mock_run_command.return_value = '{"version": "1.2.3"}'
        self.context.set("wordpress_urls", ["http://wp-test.com"])
        plugin = WordPressScannerPlugin()

        # Act
        plugin.run(self.context)

        # Assert
        mock_run_command.assert_called_once()
        results = self.context.get("wordpress_vulnerabilities")
        self.assertIn("http://wp-test.com", results)
        self.assertEqual(results["http://wp-test.com"]["version"], "1.2.3")

    @patch('cyberhunter_3d.core.plugins.impl.api_security_scanner.load_config')
    @patch('cyberhunter_3d.core.plugins.impl.api_security_scanner.ApiSecurityScannerPlugin._run_command')
    def test_api_security_scanner_plugin(self, mock_run_command, mock_load_config):
        # Arrange
        mock_load_config.return_value = {
            "tool_commands": {
                "nuclei_api_scan": "nuclei -l {input_file} -t api/ -json -o {output_file}",
                "dalfox_api_scan": "dalfox file {input_file} --json-output {output_file}"
            }
        }
        self.context.set("api_endpoints", ["http://api.test.com/v1/users"])
        plugin = ApiSecurityScannerPlugin()

        # Act
        plugin.run(self.context)

        # Assert
        self.assertEqual(mock_run_command.call_count, 2) # nuclei and dalfox

    @patch('cyberhunter_3d.core.specialized_scan_manager.PluginManager')
    def test_specialized_scan_manager(self, mock_plugin_manager):
        # Arrange
        mock_manager_instance = mock_plugin_manager.return_value
        self.context.set("live_hosts", ["http://example.com"])
        self.context.set("js_files_urls", ["http://example.com/main.js"])
        self.context.set("validated_subdomains", ["sub.example.com"])
        manager_plugin = SpecializedScanManager()

        # Act
        manager_plugin.run(self.context)

        # Assert
        mock_manager_instance.run_all_plugins.assert_called_once()
        results = self.context.get("specialized_scan_results")
        self.assertIsNotNone(results)

if __name__ == '__main__':
    unittest.main()
