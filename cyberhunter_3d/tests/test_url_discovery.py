import unittest
import os
import json
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.plugins.impl.url_discovery import URLDiscoveryPlugin
from cyberhunter_3d.core.plugins.impl.url_processor import URLProcessorPlugin
from cyberhunter_3d.core.plugins.context import ScanContext

class TestURLDiscoveryPlugins(unittest.TestCase):

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

    @patch('cyberhunter_3d.core.plugins.impl.url_discovery.load_config')
    @patch('cyberhunter_3d.core.reconnaissance.url_discovery_manager.PluginManager')
    @patch('cyberhunter_3d.web.models.db.session')
    def test_discover_urls(self, mock_db_session, mock_plugin_manager, mock_load_config):
        # --- Mock the config ---
        mock_load_config.return_value = {
            "tool_commands": {
                "gau": "gau --subs {target}",
                "waybackurls": "waybackurls {target}",
                "katana": "katana -u {target} -silent",
                "hakrawler": "hakrawler -url {target} -depth 2 -plain",
                "gau_file": "gau --subs --file {input_file}",
                "katana_list": "katana -list {input_file} -silent",
            }
        }

        # --- Mock the PluginManager and its run_all_plugins method ---
        mock_manager_instance = MagicMock()
        mock_plugin_manager.return_value = mock_manager_instance

        def side_effect(context, include_plugins=None):
            # Simulate the behavior of the plugins updating the context
            context.set("urls", ["http://example.com/url1", "http://example.com/url2"])
            context.set("live_urls", ["http://example.com/url1"])
            context.set("dead_urls", ["http://example.com/url2"])
            context.set("redirect_urls", [])
            context.set("url_parameters", ["param1", "param2"])

            # Simulate file creation by URLDiscoveryPlugin
            with open(os.path.join(self.results_dir, f"way_kat_{self.scan_id}.txt"), "w") as f:
                f.write("http://example.com/url1\nhttp://example.com/url2\n")

            # Simulate file creation by URLProcessorPlugin
            with open(os.path.join(self.results_dir, f"alive_urls_{self.scan_id}.txt"), "w") as f:
                f.write("http://example.com/url1\n")
            with open(os.path.join(self.results_dir, f"dead_urls_{self.scan_id}.txt"), "w") as f:
                f.write("http://example.com/url2\n")
            with open(os.path.join(self.results_dir, f"parameters_{self.scan_id}.txt"), "w") as f:
                f.write("param1\nparam2\n")

        mock_manager_instance.run_all_plugins.side_effect = side_effect

        # --- Mock the app and database interactions ---
        from run_web import create_app
        from cyberhunter_3d.web.models import Scan
        app = create_app()
        mock_scan = Scan(id=self.scan_id)

        # Mock the query to return the mock_scan
        mock_query = MagicMock()
        mock_query.get.return_value = mock_scan

        # This is a stand-in for the actual Scan model's query attribute
        with patch('cyberhunter_3d.web.models.Scan.query', mock_query):
            from cyberhunter_3d.core.reconnaissance.url_discovery_manager import discover_urls
            discover_urls(self.domain, self.scan_id, app)

        # --- Assertions ---
        # Check that PluginManager was called correctly
        mock_plugin_manager.assert_called_once()
        mock_manager_instance.run_all_plugins.assert_called_once()

        # Verify the included plugins
        call_args, call_kwargs = mock_manager_instance.run_all_plugins.call_args
        self.assertIn("include_plugins", call_kwargs)
        self.assertEqual(call_kwargs["include_plugins"], ["URL Discovery", "URL Processor", "Vulnerability Scanner", "Content Discovery", "JavaScript Analyzer"])

        # Check that the files were created
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, f"way_kat_{self.scan_id}.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, f"alive_urls_{self.scan_id}.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, f"dead_urls_{self.scan_id}.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.results_dir, f"parameters_{self.scan_id}.txt")))

if __name__ == '__main__':
    unittest.main()
