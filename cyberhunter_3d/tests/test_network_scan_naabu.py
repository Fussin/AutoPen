import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.plugins.impl.network_scan_naabu import NaabuScanPlugin
from cyberhunter_3d.core.plugins.context import ScanContext

class TestNaabuScanPlugin(unittest.TestCase):

    @patch('subprocess.run')
    def test_run_naabu_scan(self, mock_subprocess_run):
        # Mock the subprocess.run call
        mock_result = MagicMock()
        mock_result.stdout = """
        {"host": "localhost", "port": 80, "ip": "127.0.0.1"}
        {"host": "localhost", "port": 443, "ip": "127.0.0.1"}
        """
        mock_result.stderr = ""
        mock_result.check_returncode.return_value = None
        mock_subprocess_run.return_value = mock_result

        # Setup the plugin and context
        plugin = NaabuScanPlugin()
        context = ScanContext(target_domain="example.com", scan_id=1, results_dir="/tmp")
        context.set("validated_subdomains", {"localhost"})

        # Run the plugin
        plugin.run(context)

        # Assert the results
        open_ports = context.get("open_ports")

        self.assertIn("localhost", open_ports)
        self.assertEqual(sorted(open_ports["localhost"]), [80, 443])

if __name__ == '__main__':
    unittest.main()
