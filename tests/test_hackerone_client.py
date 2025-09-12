import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cyberhunter_3d.core.feeds.hackerone_client import get_hackerone_scopes, _parse_program_scope

# Sample H1 API Responses
SAMPLE_PROGRAMS_RESPONSE = {
    "data": [
        {
            "id": "123",
            "type": "program",
            "attributes": {
                "handle": "test-program-1"
            }
        }
    ]
}

SAMPLE_PROGRAM_DETAILS_RESPONSE = {
    "data": {
        "id": "123",
        "type": "program",
        "attributes": {
            "handle": "test-program-1"
        },
        "relationships": {
            "structured_scopes": {
                "data": [
                    {
                        "id": "1",
                        "type": "structured-scope",
                        "attributes": {
                            "asset_type": "URL",
                            "asset_identifier": "example.com",
                            "instruction": "Main website",
                            "eligible_for_submission": True
                        }
                    },
                    {
                        "id": "2",
                        "type": "structured-scope",
                        "attributes": {
                            "asset_type": "URL",
                            "asset_identifier": "staging.example.com",
                            "instruction": "Staging server",
                            "eligible_for_submission": False
                        }
                    }
                ]
            }
        }
    }
}

class TestHackerOneClient(unittest.TestCase):

    @patch('cyberhunter_3d.core.feeds.hackerone_client.requests.get')
    def test_get_hackerone_scopes_success(self, mock_get):
        # Mock the two API calls
        mock_programs_response = MagicMock()
        mock_programs_response.json.return_value = SAMPLE_PROGRAMS_RESPONSE
        mock_programs_response.raise_for_status = MagicMock()

        mock_details_response = MagicMock()
        mock_details_response.json.return_value = SAMPLE_PROGRAM_DETAILS_RESPONSE
        mock_details_response.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_programs_response, mock_details_response]

        scopes = get_hackerone_scopes("testuser", "testkey")

        self.assertEqual(len(scopes), 1)
        scope = scopes[0]
        self.assertEqual(scope['name'], 'test-program-1')
        self.assertIn('example.com', scope['targets'])
        self.assertIn('staging.example.com', scope['targets'])
        self.assertIn('example.com - Main website', scope['in_scope_rules'])
        self.assertIn('staging.example.com - Staging server', scope['out_of_scope_rules'])

    def test_parse_program_scope(self):
        parsed = _parse_program_scope(SAMPLE_PROGRAM_DETAILS_RESPONSE)
        self.assertEqual(parsed['name'], 'test-program-1')
        self.assertEqual(len(parsed['targets']), 2)
        self.assertIn('example.com', parsed['targets'])

if __name__ == '__main__':
    unittest.main()
