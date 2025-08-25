import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cyberhunter_3d.core.reconnaissance.analytics_correlation import find_related_domains_by_analytics, _find_analytics_ids_for_domain, _find_domains_for_analytics_id

# Sample gospider output
GOSPIDER_OUTPUT = """
[other-source] Found Analytics ID: UA-12345-1
[other-source] Found Analytics ID: G-ABC123DEF4
"""

# Sample gau output
GAU_OUTPUT_UA = """
http://related-domain-1.com
https://unrelated.com
http://related-domain-2.com/path
"""
GAU_OUTPUT_G = """
https://another-related.com
"""

class TestAnalyticsCorrelation(unittest.TestCase):

    @patch('cyberhunter_3d.core.reconnaissance.analytics_correlation.subprocess.run')
    def test_find_analytics_ids(self, mock_run):
        mock_run.return_value.stdout = GOSPIDER_OUTPUT
        ids = _find_analytics_ids_for_domain("example.com")
        self.assertEqual(ids, {"UA-12345-1", "G-ABC123DEF4"})

    @patch('cyberhunter_3d.core.reconnaissance.analytics_correlation.subprocess.run')
    def test_find_domains_for_id(self, mock_run):
        mock_run.return_value.stdout = GAU_OUTPUT_UA
        domains = _find_domains_for_analytics_id("UA-12345-1")
        self.assertEqual(domains, {"related-domain-1.com", "related-domain-2.com", "unrelated.com"})

    @patch('cyberhunter_3d.core.reconnaissance.analytics_correlation._find_analytics_ids_for_domain')
    @patch('cyberhunter_3d.core.reconnaissance.analytics_correlation._find_domains_for_analytics_id')
    def test_main_orchestrator_function(self, mock_find_domains, mock_find_ids):
        # Mock the helper functions to avoid actual subprocess calls
        mock_find_ids.return_value = {"UA-12345-1"}
        mock_find_domains.return_value = {"related.com", "example.com"} # It found itself and a new domain

        seed_domains = ["example.com"]
        new_domains = find_related_domains_by_analytics(seed_domains)

        mock_find_ids.assert_called_once_with("example.com")
        mock_find_domains.assert_called_once_with("UA-12345-1")

        # The result should not include the original seed domain
        self.assertEqual(new_domains, {"related.com"})

if __name__ == '__main__':
    unittest.main()
