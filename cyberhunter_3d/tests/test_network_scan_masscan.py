import unittest
from unittest.mock import patch, MagicMock
import json
import tempfile
import os

from cyberhunter_3d.core.plugins.impl.network_scan_masscan import MasscanScanPlugin
from cyberhunter_3d.core.plugins.context import ScanContext

class TestMasscanScanPlugin(unittest.TestCase):

    @patch('os.remove')
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_run_masscan_scan(self, mock_tempfile, mock_subprocess_run, mock_os_remove):
        # Mock the subprocess.run call
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.check_returncode.return_value = None
        mock_subprocess_run.return_value = mock_result

        # Mock the tempfile
        mock_output_file = MagicMock()
        mock_output_file.name = "/tmp/masscan_output.json"

        # The first call to NamedTemporaryFile is for the input file
        # The second call is for the output file
        mock_tempfile.side_effect = [
            MagicMock(), # for the input file
            mock_output_file
        ]

        # Create a dummy masscan output file
        masscan_output = [
            {"ip": "127.0.0.1", "timestamp": "1628582400", "ports": [{"port": 80, "proto": "tcp", "status": "open", "reason": "syn-ack", "ttl": 64}]},
            {"ip": "127.0.0.1", "timestamp": "1628582401", "ports": [{"port": 443, "proto": "tcp", "status": "open", "reason": "syn-ack", "ttl": 64}]}
        ]

        # Write the dummy output to the mocked file
        with open(mock_output_file.name, 'w') as f:
            for item in masscan_output:
                f.write(json.dumps(item) + '\n')


        # Setup the plugin and context
        plugin = MasscanScanPlugin()
        context = ScanContext(target_domain="example.com", scan_id=1, results_dir="/tmp")
        context.set("validated_subdomains", {"localhost"})

        # Run the plugin
        plugin.run(context)

        # Assert the results
        open_ports = context.get("open_ports")

        self.assertIn("127.0.0.1", open_ports)
        self.assertEqual(sorted(open_ports["127.0.0.1"]), [80, 443])

        # Cleanup the dummy file
        os.remove(mock_output_file.name)


if __name__ == '__main__':
    unittest.main()
