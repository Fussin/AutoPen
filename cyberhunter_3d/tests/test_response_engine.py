import unittest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.response_engine import ResponseEngine
from run_web import app

class TestResponseEngineEvents(unittest.TestCase):

    def setUp(self):
        self.validated_finding = {
            "scan_id": 1,
            "target_domain": "example.com",
            "title": "Test Vulnerability",
            "status": "Validated",
            "severity": "High",
            "disposition": None
        }
        self.critical_finding = {
            "scan_id": 1,
            "target_domain": "example.com",
            "title": "Critical Vulnerability",
            "status": "Validated",
            "severity": "Critical",
            "disposition": None
        }

    def test_critical_finding_event(self):
        """
        Verify the correct handlers are called for a CRITICAL_FINDING_DETECTED event.
        """
        with app.app_context():
            engine = ResponseEngine()
            # Mock all handlers
            for handler_name, handler_instance in engine.all_handlers.items():
                handler_instance.handle = MagicMock(return_value=f"{handler_name} handled")

            engine.run([self.critical_finding], 'CRITICAL_FINDING_DETECTED')

            # Assert that the correct handlers were called
            engine.all_handlers['slack'].handle.assert_called_once_with(self.critical_finding)
            engine.all_handlers['email'].handle.assert_called_once_with(self.critical_finding)
            engine.all_handlers['sms'].handle.assert_called_once_with(self.critical_finding)
            engine.all_handlers['dashboard'].handle.assert_called_once_with(self.critical_finding)
            engine.all_handlers['jira'].handle.assert_called_once_with(self.critical_finding)

            # Assert that other handlers were NOT called
            engine.all_handlers['report'].handle.assert_not_called()
            engine.all_handlers['archive'].handle.assert_not_called()

    def test_scan_completion_event(self):
        """
        Verify the correct handlers are called for a SCAN_COMPLETION event.
        """
        with app.app_context():
            engine = ResponseEngine()
            # Mock all handlers
            for handler_name, handler_instance in engine.all_handlers.items():
                handler_instance.handle = MagicMock(return_value=f"{handler_name} handled")

            engine.run([self.validated_finding], 'SCAN_COMPLETION')

            # Assert that the correct handlers were called
            engine.all_handlers['report'].handle.assert_called_once_with(self.validated_finding)
            engine.all_handlers['bug_bounty'].handle.assert_called_once_with(self.validated_finding)
            engine.all_handlers['archive'].handle.assert_called_once_with(self.validated_finding)
            engine.all_handlers['schedule'].handle.assert_called_once_with(self.validated_finding)

            # Assert that other handlers were NOT called
            engine.all_handlers['slack'].handle.assert_not_called()
            engine.all_handlers['jira'].handle.assert_not_called()
            engine.all_handlers['sms'].handle.assert_not_called()

if __name__ == '__main__':
    unittest.main()
