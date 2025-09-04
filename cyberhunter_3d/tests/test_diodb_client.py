import unittest
from unittest.mock import patch, MagicMock
import json
import requests

from cyberhunter_3d.core.feeds.diodb_client import get_diodb_programs

class TestDiodbClient(unittest.TestCase):

    @patch('requests.get')
    def test_get_diodb_programs_success(self, mock_get):
        """Test that the diodb client successfully fetches and parses programs."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "program_name": "Test Program 1",
                "policy_url": "https://example.com/policy1"
            },
            {
                "program_name": "Test Program 2",
                "policy_url": "https://example.com/policy2"
            }
        ]
        mock_get.return_value = mock_response

        programs = get_diodb_programs()

        self.assertEqual(len(programs), 2)
        self.assertEqual(programs[0]['name'], 'Test Program 1')
        self.assertEqual(programs[0]['targets'], ['https://example.com/policy1'])
        self.assertEqual(programs[1]['name'], 'Test Program 2')
        self.assertEqual(programs[1]['targets'], ['https://example.com/policy2'])

    @patch('requests.get')
    def test_get_diodb_programs_request_exception(self, mock_get):
        """Test that the diodb client handles a request exception."""
        mock_get.side_effect = requests.exceptions.RequestException("Test error")

        programs = get_diodb_programs()

        self.assertEqual(len(programs), 0)

    @patch('requests.get')
    def test_get_diodb_programs_json_decode_error(self, mock_get):
        """Test that the diodb client handles a JSON decode error."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Test error", "", 0)
        mock_get.return_value = mock_response

        programs = get_diodb_programs()

        self.assertEqual(len(programs), 0)

if __name__ == '__main__':
    unittest.main()
