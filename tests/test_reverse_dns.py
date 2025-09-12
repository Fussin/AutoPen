import unittest
from unittest.mock import patch
import sys
import os
import subprocess

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cyberhunter_3d.core.reconnaissance.reverse_dns import get_hostnames_for_ips

# Sample dnsx output for testing
SAMPLE_DNSX_OUTPUT = """
dns.google.
one.one.one.one.
"""

class TestReverseDns(unittest.TestCase):

    @patch('cyberhunter_3d.core.reconnaissance.reverse_dns.subprocess.run')
    def test_get_hostnames_for_ips_success(self, mock_subprocess_run):
        # Mock the subprocess call to return the sample output
        mock_subprocess_run.return_value.stdout = SAMPLE_DNSX_OUTPUT
        mock_subprocess_run.return_value.stderr = ""

        hostnames = get_hostnames_for_ips(["8.8.8.8", "1.1.1.1"])

        # Check that dnsx was called correctly
        # The exact temp file name is unknown, so we use unittest.mock.ANY
        mock_subprocess_run.assert_called_once_with(
            ['dnsx', '-l', unittest.mock.ANY, '-ptr', '-resp-only'],
            capture_output=True, text=True, check=True
        )

        # Check that the output is parsed correctly
        expected_hostnames = {"dns.google", "one.one.one.one"}
        self.assertEqual(hostnames, expected_hostnames)

    @patch('cyberhunter_3d.core.reconnaissance.reverse_dns.subprocess.run')
    def test_get_hostnames_for_ips_error(self, mock_subprocess_run):
        # Mock a failed subprocess call
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "dnsx", stderr="Some dnsx error")

        hostnames = get_hostnames_for_ips(["127.0.0.1"])
        self.assertEqual(hostnames, set())

    def test_get_hostnames_for_ips_no_input(self):
        # Test that it handles an empty list of IPs gracefully
        hostnames = get_hostnames_for_ips([])
        self.assertEqual(hostnames, set())

if __name__ == '__main__':
    unittest.main()
