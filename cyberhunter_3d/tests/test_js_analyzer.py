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
        if os.path.exists(self.results_dir):
            import shutil
            shutil.rmtree(self.results_dir)

    @patch('cyberhunter_3d.core.plugins.impl.js_analyzer.JavaScriptAnalyzerPlugin._run_command')
    @patch('cyberhunter_3d.core.plugins.impl.js_analyzer.load_config')
    def test_javascript_analyzer_plugin(self, mock_load_config, mock_run_command):
        mock_load_config.return_value = {
            "tool_commands": {
                "subjs": "subjs -i {input_file}",
                "linkfinder_file": "linkfinder.py -i {input_file} -o {output_file}",
            }
        }

        def side_effect(command):
            if "linkfinder" in command:
                output_file = command.split(" -o ")[1]
                with open(output_file, "w") as f:
                    f.write("/api/v1/users\n")
            return ""
        mock_run_command.side_effect = side_effect

        js_files = ["http://example.com/script.js"]
        self.context.set("js_files_urls", js_files)
        js_files_list_path = os.path.join(self.results_dir, "js_files.txt")
        with open(js_files_list_path, "w") as f:
            f.write("\n".join(js_files))

        plugin = JavaScriptAnalyzerPlugin()
        plugin.run(self.context)

        self.assertGreater(mock_run_command.call_count, 0)
        self.assertIsNotNone(self.context.get("js_endpoints"))
        self.assertEqual(len(self.context.get("js_endpoints")['all_js_files']), 1)

if __name__ == '__main__':
    unittest.main()
