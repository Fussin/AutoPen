import unittest
from unittest.mock import Mock, patch
from cyberhunter_3d.core.error_handler import handle_module_errors, MinorError, CriticalError

class TestErrorHandler(unittest.TestCase):

    def test_successful_execution(self):
        """
        Tests that the decorator returns the function's result on success.
        """
        @handle_module_errors()
        def successful_func():
            return "success"

        self.assertEqual(successful_func(), "success")

    def test_retry_mechanism(self):
        """
        Tests that the decorator retries the function the specified number of times.
        """
        mock_func = Mock(side_effect=[Exception("fail"), "success"])

        @handle_module_errors(retries=2)
        def func_to_retry():
            return mock_func()

        self.assertEqual(func_to_retry(), "success")
        self.assertEqual(mock_func.call_count, 2)

    def test_fallback_return_value(self):
        """
        Tests that the decorator returns the fallback value after all retries fail.
        """
        mock_func = Mock(side_effect=Exception("permanent failure"))

        @handle_module_errors(retries=3, fallback_return="fallback")
        def func_with_fallback():
            return mock_func()

        self.assertEqual(func_with_fallback(), "fallback")
        self.assertEqual(mock_func.call_count, 3)

    def test_minor_error_raised(self):
        """
        Tests that a MinorError is raised by default if no fallback is provided.
        """
        mock_func = Mock(side_effect=Exception("permanent failure"))

        @handle_module_errors(retries=1)
        def func_raising_minor_error():
            return mock_func()

        with self.assertRaises(MinorError):
            func_raising_minor_error()

    def test_critical_error_raised(self):
        """
        Tests that a CriticalError is raised when specified.
        """
        mock_func = Mock(side_effect=Exception("critical failure"))

        @handle_module_errors(retries=1, error_severity=CriticalError)
        def func_raising_critical_error():
            return mock_func()

        with self.assertRaises(CriticalError):
            func_raising_critical_error()

    @patch('time.sleep', return_value=None)
    def test_delay_between_retries(self, mock_sleep):
        """
        Tests that the decorator waits for the specified delay between retries.
        """
        mock_func = Mock(side_effect=[Exception("fail"), Exception("fail"), "success"])

        @handle_module_errors(retries=3, delay=5)
        def func_with_delay():
            return mock_func()

        func_with_delay()
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(5)

if __name__ == '__main__':
    unittest.main()
