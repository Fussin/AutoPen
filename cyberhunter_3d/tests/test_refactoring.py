import unittest
from unittest.mock import patch, MagicMock
from ..core.reconnaissance.passive_engine import run_passive_enumeration

class TestRefactoring(unittest.TestCase):

    @patch('cyberhunter_3d.core.reconnaissance.passive_engine.SubfinderPlugin')
    @patch('cyberhunter_3d.core.reconnaissance.passive_engine.run_command')
    def test_passive_engine_calls_subfinder_plugin(self, mock_run_command, mock_subfinder_plugin):
        # Arrange
        mock_plugin_instance = MagicMock()
        mock_plugin_instance.check_dependencies.return_value = True
        mock_plugin_instance.run.return_value = [{"evidence": {"poc": "test.example.com"}}]
        mock_subfinder_plugin.return_value = mock_plugin_instance

        mock_run_command.return_value = ""

        # Act
        subdomains = run_passive_enumeration("example.com")

        # Assert
        mock_subfinder_plugin.assert_called_once()
        mock_plugin_instance.run.assert_called_once_with(["example.com"])
        self.assertIn("test.example.com", subdomains)

if __name__ == '__main__':
    unittest.main()
