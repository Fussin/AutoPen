import unittest
import json
from unittest.mock import patch
from jsonschema import validate
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2

class TestSchemaValidation(unittest.TestCase):

    def get_schema(self):
        """A simplified version of the schema for validation testing."""
        return {
            "type": "object",
            "properties": {
                "metadata": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "scan_id": {"type": "string"},
                        "timestamp_utc": {"type": "string", "format": "date-time"}
                    },
                    "required": ["target", "scan_id", "timestamp_utc"]
                },
                "assets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "asset_type": {"type": "string"},
                            "value": {"type": "string"},
                            "vulnerabilities": {"type": "array"},
                            "takeover_risk": {"type": "boolean"}
                        },
                        "required": ["asset_type", "value"]
                    }
                }
            },
            "required": ["metadata", "assets"]
        }

    @patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.PluginManager')
    @patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.detect_wildcard_ips')
    @patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.resolve_and_validate')
    def test_output_conforms_to_schema(self, mock_resolve, mock_detect, mock_pm):
        """
        Test that the generated JSON output conforms to the defined schema.
        """
        # 1. Setup Mocks
        mock_resolve.return_value = {'test.example.com'}
        mock_detect.return_value = set()

        # Mock the plugin manager to return some basic data
        mock_plugin_manager = mock_pm.return_value
        mock_plugin_manager.get_all_plugins.return_value = [] # No plugins for this test

        # 2. Run the function
        output_paths = enumerate_subdomains_v2("example.com")
        self.assertTrue(output_paths)
        json_path = output_paths[0]

        # 3. Validate the output
        with open(json_path, 'r') as f:
            output_data = json.load(f)

        validate(instance=output_data, schema=self.get_schema())

if __name__ == '__main__':
    unittest.main()
