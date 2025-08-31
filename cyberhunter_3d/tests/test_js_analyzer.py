import unittest
import os
import json
from unittest.mock import patch, MagicMock, call
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
            if os.path.isdir(self.results_dir):
                import shutil
                shutil.rmtree(self.results_dir)

    @patch('cyberhunter_3d.core.plugins.impl.js_analyzer.requests.get')
    @patch('cyberhunter_3d.core.plugins.impl.js_analyzer.JavaScriptAnalyzerPlugin._run_command')
    @patch('cyberhunter_3d.core.plugins.impl.js_analyzer.load_config')
    def test_javascript_analyzer_plugin(self, mock_load_config, mock_run_command, mock_requests_get):
        # Mock config
        mock_load_config.return_value = {
            "tool_commands": {
                "subjs": "subjs -i {input_file}",
                "linkfinder_file": "linkfinder.py -i {input_file} -o {output_file}",
                "trufflehog_file": "trufflehog filesystem {url} --json",
                "retirejs_scan": "retire --path {input_path} --outputformat json"
            }
        }

        # Setup mock context and files
        js_files = ["http://example.com/script.js"]
        self.context.set("js_files_urls", js_files)
        js_files_list_path = os.path.join(self.results_dir, "js_files.txt")
        with open(js_files_list_path, "w") as f:
            f.write("\n".join(js_files))

        # Mock command outputs
        def run_command_side_effect(command):
            if "subjs" in command:
                return "http://example.com/new_url_from_js"
            if "linkfinder" in command:
                # The command creates an output file, so we simulate that
                output_file = command.split(" -o ")[1]
                with open(output_file, "w") as f:
                    f.write("/api/users\n")
                    f.write("/api/posts\n")
                return ""
            if "trufflehog" in command:
                return json.dumps({"SourceMetadata": {"Data": {"Filesystem": {"file": "http://example.com/script.js"}}}, "Raw": "var api_key = 'SECRET_KEY';"})
            if "retire" in command:
                return json.dumps({"data": []}) # No vulnerable libs
            return ""
        mock_run_command.side_effect = run_command_side_effect

        # Mock requests.get for retire.js
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"var x = 1;"
        mock_requests_get.return_value = mock_response

        # Run the plugin
        plugin = JavaScriptAnalyzerPlugin()
        plugin.run(self.context)

        # Assertions
        self.assertGreater(mock_run_command.call_count, 0)

        # Check endpoints
        js_endpoints = self.context.get("api_endpoints")
        self.assertIsNotNone(js_endpoints)
        self.assertIn("all_js_files", js_endpoints)
        self.assertEqual(len(js_endpoints["all_js_files"]), 2)
        self.assertIn("/api/users", js_endpoints["all_js_files"])

        # Check secrets
        js_secrets = self.context.get("js_secrets")
        self.assertIsNotNone(js_secrets)
        self.assertIn("http://example.com/script.js", js_secrets)
        self.assertEqual(len(js_secrets["http://example.com/script.js"]), 1)

        # Check new URLs
        new_urls = self.context.get("new_urls_from_js")
        self.assertIsNotNone(new_urls)
        self.assertIn("http://example.com/new_url_from_js", new_urls)

        # Check that result files were created
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, f"js_endpoints_{self.scan_id}.json")))
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, f"js_secrets_{self.scan_id}.json")))
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, "new_from_js.txt")))

if __name__ == '__main__':
    unittest.main()
