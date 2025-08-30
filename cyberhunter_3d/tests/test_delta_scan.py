import unittest
from unittest.mock import MagicMock
from cyberhunter_3d.core.reconnaissance.subdomain_enum import perform_delta_scan

class TestDeltaScan(unittest.TestCase):

    def test_perform_delta_scan(self):
        """
        Tests that the perform_delta_scan function correctly identifies new and
        removed subdomains.
        """
        master_subdomains = {"a.example.com", "b.example.com", "c.example.com"}
        previous_subdomains = {"a.example.com", "d.example.com"}

        logger = MagicMock()

        delta_results = perform_delta_scan(master_subdomains, previous_subdomains, logger)

        expected_new = {"b.example.com", "c.example.com"}
        expected_removed = {"d.example.com"}

        self.assertEqual(delta_results["new"], expected_new)
        self.assertEqual(delta_results["removed"], expected_removed)

    def test_perform_delta_scan_no_previous_subdomains(self):
        """
        Tests that the delta scan function does nothing if there are no
        previous subdomains to compare against.
        """
        master_subdomains = {"a.example.com", "b.example.com"}
        previous_subdomains = set()

        logger = MagicMock()

        delta_results = perform_delta_scan(master_subdomains, previous_subdomains, logger)

        self.assertEqual(delta_results, {})

if __name__ == '__main__':
    unittest.main()
