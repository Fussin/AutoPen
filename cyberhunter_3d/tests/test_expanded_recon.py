import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.plugins.impl.expanded_recon import ExpandedReconPlugin
from cyberhunter_3d.core.plugins.context import ScanContext

class TestExpandedReconPlugin(unittest.TestCase):

    def setUp(self):
        self.context = ScanContext("example.com", 1, "results")

    @patch('cyberhunter_3d.core.plugins.impl.expanded_recon.shodan.Shodan')
    def test_finds_new_domains_via_artifacts(self, MockShodan):
        """
        Tests that the plugin uses artifacts to query Shodan and finds new domains.
        """
        mock_shodan_client = MagicMock()
        mock_shodan_client.search.return_value = {
            'matches': [
                {'hostnames': ['new-domain-from-hash.com']},
                {'hostnames': ['another-domain.com', 'example.com']}
            ]
        }
        mock_shodan_client.info.return_value = {}
        MockShodan.return_value = mock_shodan_client

        artifacts = {
            "favicon_hashes": ["-123456789"],
            "google_analytics_ids": []
        }
        self.context.set("discovered_artifacts", artifacts)
        self.context.set("subdomains", {"example.com"})

        with patch.dict('os.environ', {'SHODAN_API_KEY': 'fake_key'}):
            plugin = ExpandedReconPlugin()
            plugin.run(self.context)

        mock_shodan_client.search.assert_called_once_with("http.favicon.hash:-123456789")

        expanded_targets = self.context.get("expanded_targets")
        self.assertIn("new-domain-from-hash.com", expanded_targets)
        self.assertIn("another-domain.com", expanded_targets)

        all_subdomains = self.context.get("subdomains")
        self.assertIn("new-domain-from-hash.com", all_subdomains)

if __name__ == '__main__':
    unittest.main()
