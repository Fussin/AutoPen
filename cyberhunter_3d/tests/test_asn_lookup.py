import unittest
from unittest.mock import patch
import sys
import os
import subprocess

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cyberhunter_3d.core.reconnaissance.asn_lookup import get_cidrs_for_asn, get_asn_for_ips
from unittest.mock import MagicMock

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

        from cyberhunter_3d.core.reconnaissance.utils import load_config
        config = load_config()
        amass_path = config['tools']['amass']

        # Check that amass was called correctly
        mock_subprocess_run.assert_called_once_with(
            [amass_path, 'intel', '-asn', '15169'],
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

    @patch('cyberhunter_3d.core.reconnaissance.asn_lookup.subprocess.run')
    def test_get_asn_for_ips(self, mock_run):
        """
        Tests the get_asn_for_ips function to ensure it correctly parses dnsx JSON output.
        """
        # Mock the JSON output from the dnsx tool
        dnsx_output = (
            '{"host":"8.8.8.8","asn":{"asn":"AS15169","name":"GOOGLE","country":"US","registrar":"ARIN"}}\n'
            '{"host":"1.1.1.1","asn":{"asn":"AS13335","name":"CLOUDFLARENET","country":"US","registrar":"ARIN"}}\n'
        )
        mock_process = MagicMock()
        mock_process.stdout = dnsx_output
        mock_run.return_value = mock_process

        ips = {'8.8.8.8', '1.1.1.1'}
        asn_details = get_asn_for_ips(ips)

        # Assertions
        self.assertEqual(len(asn_details), 2)
        self.assertIn('8.8.8.8', asn_details)
        self.assertIn('1.1.1.1', asn_details)
        self.assertEqual(asn_details['8.8.8.8']['asn'], 'AS15169')
        self.assertEqual(asn_details['1.1.1.1']['name'], 'CLOUDFLARENET')
        mock_run.assert_called_once()

if __name__ == '__main__':
    unittest.main()
