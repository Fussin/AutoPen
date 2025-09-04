import unittest
from unittest.mock import patch, MagicMock
from collections import deque

from cyberhunter_3d.core.data_pipeline import DataPipeline


class TestDataPipeline(unittest.TestCase):

    def setUp(self):
        """Set up a mock config for all tests."""
        self.mock_config = {
            'data_pipeline': {
                'in_scope_rules': '*.example.com',
                'out_of_scope_rules': 'dev.example.com'
            },
            'hackerone': {
                'api_user': 'test_user',
                'api_key': 'test_key'
            },
            'bugcrowd': {
                'api_user': 'test_user',
                'api_key': 'test_key'
            }
        }

    def test_pipeline_initialization_with_config(self):
        """Test that the pipeline initializes correctly with a config object."""
        pipeline = DataPipeline(config=self.mock_config)
        self.assertIsNotNone(pipeline.scope_validator)
        # Check that the rules from the mock config were loaded
        self.assertEqual(len(pipeline.scope_validator.in_scope_patterns), 1)
        self.assertEqual(len(pipeline.scope_validator.out_of_scope_patterns), 1)
        self.assertEqual(pipeline.h1_user, 'test_user')
        self.assertEqual(pipeline.h1_key, 'test_key')

    @patch('cyberhunter_3d.core.data_pipeline.load_config')
    def test_pipeline_initialization_loads_default_config(self, mock_load_config):
        """Test that the pipeline loads the default config if none is provided."""
        mock_load_config.return_value = self.mock_config
        pipeline = DataPipeline()
        self.assertIsNotNone(pipeline.scope_validator)
        mock_load_config.assert_called_once()
        self.assertEqual(len(pipeline.scope_validator.in_scope_patterns), 1)

    def test_parsing_and_validation(self):
        """Test the parsing of raw targets and scope validation using the mock config."""
        pipeline = DataPipeline(config=self.mock_config)
        raw_targets = [
            "test.example.com",
            "dev.example.com",
            "another.com",
            "192.168.1.1",
        ]
        validated = pipeline._parse_and_validate(raw_targets)
        validated_values = {val for val, typ in validated}
        self.assertIn("test.example.com", validated_values)
        self.assertIn("192.168.1.1", validated_values)
        self.assertNotIn("dev.example.com", validated_values)
        self.assertNotIn("another.com", validated_values)

    def test_normalization_and_deduplication(self):
        """Test that the pipeline correctly normalizes and deduplicates targets."""
        pipeline = DataPipeline(config=self.mock_config)
        targets_with_duplicates = [
            ("test.example.com", "domain"),
            ("test.example.com", "domain"),
            ("192.168.1.1", "ip_address"),
        ]
        normalized = pipeline._normalize(targets_with_duplicates)
        self.assertEqual(len(normalized), 2)

    def test_prioritization(self):
        """Test the prioritization of targets."""
        pipeline = DataPipeline(config=self.mock_config)
        unsorted_targets = [
            ("192.168.1.1", "ip_address"),
            ("test.example.com", "domain"),
        ]
        prioritized_queue = pipeline._prioritize(unsorted_targets)
        self.assertEqual(prioritized_queue.popleft(), ("test.example.com", "domain"))
        self.assertEqual(prioritized_queue.popleft(), ("192.168.1.1", "ip_address"))

    @patch('cyberhunter_3d.core.data_pipeline.get_diodb_programs')
    @patch('cyberhunter_3d.core.data_pipeline.get_bugcrowd_programs')
    @patch('cyberhunter_3d.core.data_pipeline.get_hackerone_scopes')
    def test_run_autonomous_mode(self, mock_get_h1_scopes, mock_get_bc_scopes, mock_get_diodb_programs):
        """Test the end-to-end autonomous run with all three data sources."""
        mock_h1_programs = [
            {
                'name': 'h1-program',
                'targets': ['h1.example.com'],
                'in_scope_rules': '*.example.com',
                'out_of_scope_rules': ''
            }
        ]
        mock_bc_programs = [
            {
                'name': 'bc-program',
                'targets': ['bc.example.com'],
                'in_scope_rules': '*.example.com',
                'out_of_scope_rules': ''
            }
        ]
        mock_diodb_programs = [
            {
                'name': 'diodb-program',
                'targets': ['diodb.example.com'],
                'in_scope_rules': '*.example.com',
                'out_of_scope_rules': ''
            }
        ]
        mock_get_h1_scopes.return_value = mock_h1_programs
        mock_get_bc_scopes.return_value = mock_bc_programs
        mock_get_diodb_programs.return_value = mock_diodb_programs

        pipeline = DataPipeline(config=self.mock_config)

        programs = pipeline.run_autonomous()

        mock_get_h1_scopes.assert_called_once_with('test_user', 'test_key')
        mock_get_bc_scopes.assert_called_once_with('test_user', 'test_key')
        mock_get_diodb_programs.assert_called_once()

        self.assertEqual(len(programs), 3)
        self.assertEqual(programs[0]['name'], 'h1-program')
        self.assertEqual(programs[1]['name'], 'bc-program')
        self.assertEqual(programs[2]['name'], 'diodb-program')

if __name__ == '__main__':
    unittest.main()
