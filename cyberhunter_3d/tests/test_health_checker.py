import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.health_checker import check_command, run_health_checks

class TestHealthChecker(unittest.TestCase):

    @patch('shutil.which')
    def test_check_command_found(self, mock_which):
        """
        Tests that check_command returns True when the command is found.
        """
        mock_which.return_value = '/usr/bin/test'
        self.assertTrue(check_command('test'))

    @patch('shutil.which')
    def test_check_command_not_found(self, mock_which):
        """
        Tests that check_command returns False when the command is not found.
        """
        mock_which.return_value = None
        self.assertFalse(check_command('nonexistent'))

    @patch('cyberhunter_3d.core.health_checker.check_command')
    def test_run_health_checks_all_pass(self, mock_check_command):
        """
        Tests that run_health_checks returns True when all checks pass.
        """
        mock_check_command.return_value = True
        self.assertTrue(run_health_checks())

    @patch('cyberhunter_3d.core.health_checker.check_command')
    def test_run_health_checks_one_fails(self, mock_check_command):
        """
        Tests that run_health_checks returns False when one check fails.
        """
        mock_check_command.side_effect = [True, False, True, True, True, True]
        self.assertFalse(run_health_checks())

if __name__ == '__main__':
    unittest.main()
