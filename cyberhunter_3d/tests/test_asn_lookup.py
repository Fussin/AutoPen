import unittest
from unittest.mock import patch
import sys
import os
import subprocess

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cyberhunter_3d.core.reconnaissance.asn_lookup import get_cidrs_for_asn

# Sample amass output for testing
SAMPLE_AMASS_OUTPUT = """
8.8.8.0/24
8.8.4.0/24
35.192.0.0/12
104.154.0.0/15
"""

class TestAsnLookup(unittest.TestCase):

    @patch('cyberhunter_3d.core.reconnaissance.asn_lookup.subprocess.run')
    def test_get_cidrs_for_asn_success(self, mock_subprocess_run):
        # Mock the subprocess call to return the sample output
        mock_subprocess_run.return_value.stdout = SAMPLE_AMASS_OUTPUT.strip()
        mock_subprocess_run.return_value.stderr = ""

        assets = get_cidrs_for_asn("15169")

        # Check that amass was called correctly
        mock_subprocess_run.assert_called_once_with(
            ['amass', 'intel', '-asn', '15169'],
            capture_output=True, text=True, check=True
        )

        # Check that the output is parsed correctly
        self.assertEqual(len(assets), 4)
        expected_assets = [
            {'type': 'cidr', 'value': '8.8.8.0/24'},
            {'type': 'cidr', 'value': '8.8.4.0/24'},
            {'type': 'cidr', 'value': '35.192.0.0/12'},
            {'type': 'cidr', 'value': '104.154.0.0/15'}
        ]
        self.assertCountEqual(assets, expected_assets)

    @patch('cyberhunter_3d.core.reconnaissance.asn_lookup.subprocess.run')
    def test_get_cidrs_for_asn_amass_error(self, mock_subprocess_run):
        # Mock a failed subprocess call
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "amass", stderr="Some amass error")

        cidrs = get_cidrs_for_asn("15169")
        self.assertEqual(len(cidrs), 0)

    @patch('cyberhunter_3d.core.reconnaissance.asn_lookup.subprocess.run')
    def test_get_cidrs_for_asn_no_output(self, mock_subprocess_run):
        # Mock a successful call with no output
        mock_subprocess_run.return_value.stdout = ""

        cidrs = get_cidrs_for_asn("00000")
        self.assertEqual(len(cidrs), 0)

if __name__ == '__main__':
    unittest.main()
