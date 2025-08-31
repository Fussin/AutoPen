import unittest
from unittest.mock import patch, MagicMock
import json
import tempfile
import shutil
from cyberhunter_3d.core.plugins.impl.wordpress_scanner import WordPressScannerPlugin
from cyberhunter_3d.core.plugins.impl.api_security_scanner import ApiSecurityScannerPlugin
from cyberhunter_3d.core.plugins.impl.api_spec_finder import ApiSpecFinderPlugin
from cyberhunter_3d.core.plugins.impl.js_analyzer import JavaScriptAnalyzerPlugin
from cyberhunter_3d.core.plugins.impl.cloud_enum import CloudEnumPlugin
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

    @patch('requests.get')
    def test_api_spec_finder_plugin(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"paths": {"/api/v1/users": {}, "/api/v1/posts": {}}}
        mock_get.return_value = mock_response

        self.context.set("live_hosts", ["http://api.test.com"])
        plugin = ApiSpecFinderPlugin()

        # Act
        plugin.run(self.context)

        # Assert
        self.assertTrue(mock_get.called)
        results = self.context.get("spec_endpoints")
        self.assertIn("http://api.test.com", results)
        self.assertIn("/api/v1/users", results["http://api.test.com"])
        self.assertIn("/api/v1/posts", results["http://api.test.com"])

    @patch('cyberhunter_3d.core.plugins.impl.api_security_scanner.load_config')
    @patch('cyberhunter_3d.core.plugins.impl.api_security_scanner.ApiSecurityScannerPlugin._run_scans')
    def test_api_security_scanner_plugin(self, mock_run_scans, mock_load_config):
        # Arrange
        mock_load_config.return_value = {
            "tool_commands": {
                "nuclei_api_scan": "nuclei -l {input_file} -t api/ -json -o {output_file}",
                "dalfox_api_scan": "dalfox file {input_file} --json-output {output_file}",
                "nuclei_graphql_scan": "nuclei -l {input_file} -t graphql/ -json -o {output_file}"
            }
        }
        self.context.set("api_endpoints", {"http://api.test.com": ["/api/v1/users"]})
        self.context.set("spec_endpoints", {"http://api.test.com": ["/api/v1/posts"]})
        plugin = ApiSecurityScannerPlugin()

        # Act
        plugin.run(self.context)

        # Assert
        self.assertEqual(mock_run_scans.call_count, 2)

    @patch('cyberhunter_3d.core.plugins.impl.js_analyzer.load_config')
    @patch('cyberhunter_3d.core.plugins.impl.js_analyzer.JavaScriptAnalyzerPlugin._run_command')
    @patch('requests.get')
    def test_javascript_analyzer_plugin_vulnerable_libs(self, mock_get, mock_run_command, mock_load_config):
        # Arrange
        mock_load_config.return_value = {
            "tool_commands": {
                "retirejs_scan": "retire --js --outputformat json --path {input_path}"
            }
        }
        # Mock requests.get to simulate downloading the JS file
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"var a = 1;"
        mock_get.return_value = mock_response

        mock_run_command.return_value = '{"data": [{"file": "jquery.js", "results": [{"version": "1.7.1"}]}]}'
        self.context.set("js_files_urls", ["http://example.com/jquery.js"])
        plugin = JavaScriptAnalyzerPlugin()

        # Act
        plugin.run(self.context)

        # Assert
        results = self.context.get("js_vulnerable_libraries")
        self.assertIsNotNone(results)
        self.assertEqual(len(results.get("data", [])), 1)

    @patch('cyberhunter_3d.core.plugins.impl.cloud_enum.load_config')
    @patch('cyberhunter_3d.core.plugins.impl.cloud_enum.CloudEnumPlugin._run_command')
    def test_cloud_enum_plugin_azure(self, mock_run_command, mock_load_config):
        # Arrange
        mock_load_config.return_value = {
            "tool_commands": {
                "s3_scan": "s3scanner scan -f {input_file}",
                "blobhunter_scan": "blobhunter -f {input_file}"
            }
        }

        def side_effect(command):
            if "blobhunter" in command:
                return '{"container": "https://test.blob.core.windows.net/public", "status": "Public"}'
            else:
                return ""

        mock_run_command.side_effect = side_effect
        self.context.set("validated_subdomains", ["test.example.com"])
        plugin = CloudEnumPlugin()

        # Act
        plugin.run(self.context)

        # Assert
        results = self.context.get("cloud_assets")
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['type'], 'azure_blob')

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
