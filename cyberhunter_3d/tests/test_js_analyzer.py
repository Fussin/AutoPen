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
    @patch('cyberhunter_3d.core.plugins.impl.js_analyzer.subprocess.check_output')
    @patch('cyberhunter_3d.core.plugins.impl.js_analyzer.subprocess.Popen')
    def test_javascript_analyzer_plugin(self, mock_subprocess_popen, mock_check_output, mock_load_config):
        mock_check_output.return_value = "/go"
        # Mock config
    def test_javascript_analyzer_plugin(self, mock_load_config, mock_run_command):
        # Mock config to make the plugin run

        mock_load_config.return_value = {
            "tool_commands": {
                "subjs": "subjs -i {input_file}",
                "linkfinder_file": "linkfinder.py -i {input_file} -o {output_file}",

                "trufflehog_file": "trufflehog --json {url}"
            }
        }

        # Setup mock context and files
        js_files = ["http://example.com/script.js"]
        self.context.set("js_files_urls", js_files)

        # Mock LinkFinder output
        def side_effect(*args, **kwargs):
            command = args[0]
            print(f"side_effect command: {command}")
            stdout = ""
            if "linkfinder" in command:
                output_file = command.split(" -o ")[1]
                with open(output_file, "w") as f:
                    f.write("/api/users\n")
                    f.write("/api/posts\n")
                with open(output_file, "r") as f:
                    stdout = f.read()
            mock_process = MagicMock()
            mock_process.communicate.return_value = (stdout, '')
            mock_process.returncode = 0
            return mock_process

        mock_subprocess_popen.side_effect = side_effect

            }
        }

        # Mock the command runner to create the output file when linkfinder is called
        def side_effect(command):
            if "linkfinder" in command:
                output_file = command.split(" -o ")[1]
                with open(output_file, "w") as f:
                    f.write("/api/v1/users\n")
            return ""
        mock_run_command.side_effect = side_effect

        # Setup mock context
        js_files = ["http://example.com/script.js"]
        self.context.set("js_files_urls", js_files)
        js_files_list_path = os.path.join(self.results_dir, "js_files.txt")
        with open(js_files_list_path, "w") as f:
            f.write("\n".join(js_files))


        # Run the plugin
        plugin = JavaScriptAnalyzerPlugin()
        plugin.run(self.context)


        # Assertions
        self.assertEqual(mock_subprocess_popen.call_count, 3)
        js_endpoints = self.context.get("js_endpoints")
        self.assertIsNotNone(js_endpoints)
        self.assertIn("all_js_files", js_endpoints)
        self.assertEqual(len(js_endpoints["all_js_files"]), 2)
        self.assertIn("/api/users", js_endpoints["all_js_files"])

        # Check that the results file was created
        results_file_path = os.path.join(self.results_dir, f"js_endpoints_{self.scan_id}.json")
        self.assertTrue(os.path.exists(results_file_path))
        with open(results_file_path, "r") as f:
            data = json.load(f)
            self.assertIn("all_js_files", data)
            self.assertEqual(len(data["all_js_files"]), 2)

        # Assert that the command runner was called
        self.assertGreater(mock_run_command.call_count, 0)
        # Assert that some results were set in the context
        self.assertIsNotNone(self.context.get("js_endpoints"))
        self.assertEqual(len(self.context.get("js_endpoints")['all_js_files']), 1)


if __name__ == '__main__':
    unittest.main()
