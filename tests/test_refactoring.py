import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.reconnaissance.passive_engine import run_passive_enumeration

class TestRefactoring(unittest.TestCase):

    @patch('cyberhunter_3d.core.reconnaissance.passive_engine.check_tool')
    def test_passive_engine_calls_subfinder_plugin(self, mock_check_tool):
        # Arrange
        mock_check_tool.return_value = "/fake/path/to/tool"

        with patch('cyberhunter_3d.core.reconnaissance.passive_engine.run_command') as mock_run_command:
            mock_run_command.return_value = "test.example.com\n"

            # Act
            subdomains = run_passive_enumeration("example.com")

            # Assert
            self.assertGreater(mock_run_command.call_count, 0)
            self.assertIn("test.example.com", subdomains)

if __name__ == '__main__':
    unittest.main()
