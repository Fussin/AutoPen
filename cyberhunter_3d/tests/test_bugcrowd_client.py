import unittest
from unittest.mock import patch, MagicMock

from cyberhunter_3d.core.feeds.bugcrowd_client import get_bugcrowd_programs

class TestBugcrowdClient(unittest.TestCase):

    @patch('requests.get')
    def test_get_bugcrowd_programs_success(self, mock_get):
        """
        Test that the get_bugcrowd_programs function successfully fetches and parses programs.
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "type": "program",
                    "id": "program1",
                    "attributes": { "name": "Test Program 1" },
                    "relationships": {
                        "target_groups": {
                            "data": [
                                {"type": "target_group", "id": "tg1"}
                            ]
                        }
                    }
                }
            ],
            "included": [
                {
                    "type": "target_group",
                    "id": "tg1",
                    "relationships": {
                        "targets": {
                            "data": [
                                {"type": "target", "id": "t1"},
                                {"type": "target", "id": "t2"}
                            ]
                        }
                    }
                },
                {
                    "type": "target",
                    "id": "t1",
                    "attributes": { "name": "app.example.com" }
                },
                {
                    "type": "target",
                    "id": "t2",
                    "attributes": { "name": "*.api.example.com" }
                }
            ],
            "links": {
                "next": None
            }
        }
        mock_get.return_value = mock_response

        programs = get_bugcrowd_programs("test_user", "test_key")

        self.assertEqual(len(programs), 1)
        program = programs[0]
        self.assertEqual(program['name'], "Test Program 1")
        self.assertEqual(len(program['targets']), 2)
        self.assertIn("app.example.com", program['targets'])
        self.assertIn("*.api.example.com", program['targets'])
        self.assertIn("app.example.com", program['in_scope_rules'])

        mock_get.assert_called_once()

if __name__ == '__main__':
    unittest.main()
