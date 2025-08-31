import unittest
import os
import json
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.plugins.impl.js_analyzer import JavaScriptAnalyzerPlugin
from cyberhunter_3d.core.plugins.context import ScanContext

class TestJavaScriptAnalyzerPlugin(unittest.TestCase):

    def setUp(self):
        self.domain = "example.com"
        self.scan_id = 1
        self.results_dir = f"cyberhunter_3d/recon_results/test_{self.domain}_{self.scan_id}"
        os.makedirs(self.results_dir, exist_ok=True)
        self.context = ScanContext(self.domain, self.scan_id, self.results_dir)

    def tearDown(self):
        # Clean up the results directory
        if os.path.exists(self.results_dir):
            for f in os.listdir(self.results_dir):
                os.remove(os.path.join(self.results_dir, f))
            os.rmdir(self.results_dir)

    @patch('cyberhunter_3d.core.plugins.impl.js_analyzer.load_config')
    @patch('cyberhunter_3d.core.plugins.impl.js_analyzer.subprocess.Popen')
    def test_javascript_analyzer_plugin(self, mock_subprocess_popen, mock_load_config):
        # Mock config
        mock_load_config.return_value = {
            "tool_commands": {
                "linkfinder": "linkfinder.py -i {url} -o cli"
            }
        }

        # Setup mock context and files
        live_urls = ["http://example.com/script.js", "http://example.com/page.html"]
        self.context.set("live_urls", live_urls)

        # Mock LinkFinder output
        mock_process = MagicMock()
        mock_process.communicate.return_value = ('/api/users\n/api/posts', '')
        mock_process.returncode = 0
        mock_subprocess_popen.return_value = mock_process

        # Run the plugin
        plugin = JavaScriptAnalyzerPlugin()
        plugin.run(self.context)

        # Assertions
        mock_subprocess_popen.assert_called_once()
        js_endpoints = self.context.get("js_endpoints")
        self.assertIsNotNone(js_endpoints)
        self.assertIn("http://example.com/script.js", js_endpoints)
        self.assertEqual(len(js_endpoints["http://example.com/script.js"]), 2)
        self.assertIn("/api/users", js_endpoints["http://example.com/script.js"])

        # Check that the results file was created
        results_file_path = os.path.join(self.results_dir, f"js_endpoints_{self.scan_id}.json")
        self.assertTrue(os.path.exists(results_file_path))
        with open(results_file_path, "r") as f:
            data = json.load(f)
            self.assertIn("http://example.com/script.js", data)

if __name__ == '__main__':
    unittest.main()
