import unittest
import os
import json
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.plugins.impl.content_discovery import ContentDiscoveryPlugin
from cyberhunter_3d.core.plugins.context import ScanContext

class TestContentDiscoveryPlugin(unittest.TestCase):

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

    @patch('cyberhunter_3d.core.plugins.impl.content_discovery.load_config')
    @patch('cyberhunter_3d.core.plugins.impl.content_discovery.subprocess.run')
    def test_content_discovery_plugin(self, mock_subprocess_run, mock_load_config):
        # Mock config
        mock_load_config.return_value = {
            "tool_commands": {
                "gobuster": "gobuster dir -u {url} -w {wordlist} -q -o {output_file}"
            },
            "wordlists": {
                "dir_bruteforce": "/path/to/wordlist.txt"
            }
        }

        # Setup mock context and files
        live_urls = ["http://example.com"]
        self.context.set("live_urls", live_urls)

        # Mock gobuster output
        def side_effect(command, shell, check, capture_output, text):
            output_file = command.split(" -o ")[1]
            with open(output_file, "w") as f:
                f.write("/admin (Status: 301)\n")
                f.write("/api (Status: 200)\n")
            return MagicMock(returncode=0)

        mock_subprocess_run.side_effect = side_effect

        # Run the plugin
        plugin = ContentDiscoveryPlugin()
        plugin.run(self.context)

        # Assertions
        mock_subprocess_run.assert_called_once()
        discovered_paths = self.context.get("discovered_paths")
        self.assertIsNotNone(discovered_paths)
        self.assertIn("http://example.com", discovered_paths)
        self.assertEqual(len(discovered_paths["http://example.com"]), 2)
        self.assertIn("/admin", discovered_paths["http://example.com"])

        # Check that the results file was created
        results_file_path = os.path.join(self.results_dir, f"discovered_paths_{self.scan_id}.json")
        self.assertTrue(os.path.exists(results_file_path))
        with open(results_file_path, "r") as f:
            data = json.load(f)
            self.assertIn("http://example.com", data)

if __name__ == '__main__':
    unittest.main()
