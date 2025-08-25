import unittest
from unittest.mock import patch
import sys
import os
import subprocess

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cyberhunter_3d.core.reconnaissance.org_lookup import get_assets_for_org

# Sample amass output for testing
SAMPLE_AMASS_OUTPUT = """
104.154.0.0/15
example.com
another.com [DigitalOcean]
8.8.8.0/24
*.wildcard.com
"""

class TestOrgLookup(unittest.TestCase):

    @patch('cyberhunter_3d.core.reconnaissance.org_lookup.subprocess.run')
    def test_get_assets_for_org_success(self, mock_subprocess_run):
        # Mock the subprocess call to return the sample output
        mock_subprocess_run.return_value.stdout = SAMPLE_AMASS_OUTPUT
        mock_subprocess_run.return_value.stderr = ""

        assets = get_assets_for_org("Example Org")

        # Check that amass was called correctly
        mock_subprocess_run.assert_called_once_with(
            ['amass', 'intel', '-org', 'Example Org'],
            capture_output=True, text=True, check=True
        )

        # Check that the output is parsed correctly
        expected_assets = {
            ("104.154.0.0/15", "cidr"),
            ("example.com", "domain"),
            ("another.com", "domain"),
            ("8.8.8.0/24", "cidr"),
            ("wildcard.com", "wildcard_domain"),
        }
        self.assertEqual(assets, expected_assets)

    @patch('cyberhunter_3d.core.reconnaissance.org_lookup.subprocess.run')
    def test_get_assets_for_org_amass_error(self, mock_subprocess_run):
        # Mock a failed subprocess call
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "amass", stderr="Some amass error")

        assets = get_assets_for_org("Example Org")
        self.assertEqual(len(assets), 0)

if __name__ == '__main__':
    unittest.main()
