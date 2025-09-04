import unittest
from collections import deque

from cyberhunter_3d.core.data_pipeline import DataPipeline


class TestDataPipeline(unittest.TestCase):

    def test_pipeline_initialization(self):
        """Test that the pipeline initializes correctly with scope rules."""
        in_scope = "*.example.com"
        out_of_scope = "dev.example.com"
        pipeline = DataPipeline(in_scope_rules=in_scope, out_of_scope_rules=out_of_scope)
        self.assertIsNotNone(pipeline.scope_validator)
        self.assertEqual(len(pipeline.scope_validator.in_scope_patterns), 1)
        self.assertEqual(len(pipeline.scope_validator.out_of_scope_patterns), 1)

    def test_parsing_and_validation(self):
        """Test the parsing of raw targets and scope validation."""
        in_scope = "*.example.com"
        out_of_scope = "ignore.example.com"
        pipeline = DataPipeline(in_scope_rules=in_scope, out_of_scope_rules=out_of_scope)

        raw_targets = [
            "test.example.com",          # In scope
            "ignore.example.com",        # Out of scope
            "another.com",               # Out of scope (doesn't match in_scope)
            "192.168.1.1",               # In scope (IPs are not checked against domain rules)
            "AS15169",                   # In scope (ASNs are not checked)
            "   ",                       # Empty, should be ignored
            "invalid-tld",               # Unknown type, should be ignored
        ]

        # Manually call the internal method for focused testing
        validated = pipeline._parse_and_validate(raw_targets)

        # Extract just the values for easier comparison
        validated_values = {val for val, typ in validated}

        self.assertIn("test.example.com", validated_values)
        self.assertIn("192.168.1.1", validated_values)
        self.assertIn("15169", validated_values) # ASNs are normalized to numbers
        self.assertNotIn("ignore.example.com", validated_values)
        self.assertNotIn("another.com", validated_values)
        self.assertNotIn("invalid-tld", validated_values)

    def test_normalization_and_deduplication(self):
        """Test that the pipeline correctly normalizes and deduplicates targets."""
        pipeline = DataPipeline()
        targets_with_duplicates = [
            ("test.example.com", "domain"),
            ("test.example.com", "domain"),  # Duplicate
            ("192.168.1.1", "ip_address"),
            ("192.168.1.1", "ip_address"),  # Duplicate
        ]

        normalized = pipeline._normalize(targets_with_duplicates)

        self.assertEqual(len(normalized), 2)
        self.assertIn(("test.example.com", "domain"), normalized)
        self.assertIn(("192.168.1.1", "ip_address"), normalized)

    def test_prioritization(self):
        """Test the prioritization of targets."""
        pipeline = DataPipeline()
        unsorted_targets = [
            ("192.168.1.1", "ip_address"),
            ("*.example.com", "wildcard_domain"),
            ("test.example.com", "domain"),
            ("10.0.0.0/8", "cidr"),
        ]

        prioritized_queue = pipeline._prioritize(unsorted_targets)

        self.assertIsInstance(prioritized_queue, deque)
        # Check order based on priority map
        self.assertEqual(prioritized_queue.popleft(), ("test.example.com", "domain"))
        self.assertEqual(prioritized_queue.popleft(), ("*.example.com", "wildcard_domain"))
        self.assertEqual(prioritized_queue.popleft(), ("192.168.1.1", "ip_address"))
        self.assertEqual(prioritized_queue.popleft(), ("10.0.0.0/8", "cidr"))

    def test_end_to_end_run(self):
        """Test the full pipeline run method."""
        in_scope = "*.example.com"
        out_of_scope = "dev.example.com"
        pipeline = DataPipeline(in_scope_rules=in_scope, out_of_scope_rules=out_of_scope)

        raw_targets = [
            "test.example.com",
            "www.example.com",
            "dev.example.com",   # Out of scope
            "test.example.com",  # Duplicate
            "192.168.1.1",
        ]

        result_queue = pipeline.run(raw_targets)

        # Expected order: domain > ip_address
        # Note: set operation in _normalize may change order, but sorting in _prioritize fixes it.
        # Let's convert to a list to check contents, as order is partly non-deterministic
        # due to the set operation in normalization.
        result_list = list(result_queue)

        # Check length (should be 3 unique, in-scope targets)
        self.assertEqual(len(result_list), 3)

        # Check for presence of expected targets
        self.assertIn(("test.example.com", "domain"), result_list)
        self.assertIn(("www.example.com", "domain"), result_list)
        self.assertIn(("192.168.1.1", "ip_address"), result_list)

        # Check that out-of-scope and duplicates are gone
        self.assertNotIn(("dev.example.com", "domain"), result_list)

if __name__ == '__main__':
    unittest.main()
