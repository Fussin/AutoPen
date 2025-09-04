import unittest
from unittest.mock import patch
from cyberhunter_3d.core.notifications.notification_manager import NotificationManager

class TestNotificationManager(unittest.TestCase):

    def setUp(self):
        self.notification_manager = NotificationManager()

    @patch.object(NotificationManager, 'send_slack_notification')
    def test_send_notification_slack(self, mock_send_slack):
        """
        Verify that send_notification calls the correct method for the 'slack' channel.
        """
        self.notification_manager.send_notification('slack', 'test message', {'detail': 'value'})
        mock_send_slack.assert_called_once_with('test message', {'detail': 'value'})

    @patch.object(NotificationManager, 'send_email_notification')
    def test_send_notification_email(self, mock_send_email):
        """
        Verify that send_notification calls the correct method for the 'email' channel.
        """
        self.notification_manager.send_notification('email', 'test message', {'detail': 'value'})
        mock_send_email.assert_called_once_with('test message', {'detail': 'value'})

    @patch.object(NotificationManager, 'send_sms_notification')
    def test_send_notification_sms(self, mock_send_sms):
        """
        Verify that send_notification calls the correct method for the 'sms' channel.
        """
        self.notification_manager.send_notification('sms', 'test message', {'detail': 'value'})
        mock_send_sms.assert_called_once_with('test message', {'detail': 'value'})

    def test_send_notification_unknown_channel(self):
        """
        Verify that send_notification handles an unknown channel gracefully.
        """
        # This should not raise an exception
        result = self.notification_manager.send_notification('unknown', 'test message')
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
