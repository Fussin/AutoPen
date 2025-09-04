import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.plugins.impl.permutation_enum import PermutationEnumPlugin
from cyberhunter_3d.core.plugins.context import ScanContext

class TestPermutationEnumPlugin(unittest.TestCase):

    @patch('cyberhunter_3d.core.plugins.impl.permutation_enum.PermutationEnumPlugin._get_previous_subdomains')
    @patch('cyberhunter_3d.core.plugins.impl.permutation_enum.run_command')
    @patch('cyberhunter_3d.core.plugins.impl.permutation_enum.PermutationEnumPlugin._validate_subdomains')
    def test_run_permutation_enum(self, mock_validate, mock_run_command, mock_get_previous):
        plugin = PermutationEnumPlugin()
        context = ScanContext(target_domain="example.com")

        mock_get_previous.return_value = ["dev.api.example.com", "staging.api.example.com"]

        mock_run_command.return_value = "test.example.com\nprod.example.com"

        mock_validate.return_value = {"test.example.com", "prod.example.com"}

        plugin.run(context)

        mock_get_previous.assert_called_once_with("example.com")
        mock_run_command.assert_called_once()
        mock_validate.assert_called_once()

        self.assertIn("permutation_subdomains", context)
        self.assertEqual(context.get("permutation_subdomains"), {"test.example.com", "prod.example.com"})

if __name__ == '__main__':
    unittest.main()
