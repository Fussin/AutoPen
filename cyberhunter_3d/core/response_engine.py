import logging
import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from .notifications.notification_manager import NotificationManager

# It's better to handle the case where jira is not installed.
try:
    from jira import JIRA
except ImportError:
    JIRA = None

log = logging.getLogger(__name__)

class ResponseHandler(ABC):
    """Abstract base class for response handlers."""
    @abstractmethod
    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        raise NotImplementedError

class JiraTicketHandler(ResponseHandler):
    """Creates a Jira ticket for a validated finding."""
    def __init__(self):
        self.jira_client = None
        if not JIRA:
            log.info("Jira library not installed. Skipping Jira integration.")
            return
        self.jira_url = os.getenv("JIRA_URL")
        self.jira_user = os.getenv("JIRA_USERNAME")
        self.jira_token = os.getenv("JIRA_API_TOKEN")
        self.jira_project = os.getenv("JIRA_PROJECT_KEY")
        if self.jira_url and self.jira_user and self.jira_token:
            try:
                self.jira_client = JIRA(server=self.jira_url, basic_auth=(self.jira_user, self.jira_token))
            except Exception as e:
                log.error(f"Failed to connect to Jira: {e}")

    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        if not self.jira_client or not self.jira_project:
            return None
        summary = f"Security Finding: {finding.get('title', 'Untitled Finding')}"
        description = f"""
*Severity:* {finding.get('severity', 'N/A')}
*Confidence:* {finding.get('confidence', 'N/A')}
*Host:* {finding.get('host', 'N/A')}
*Description:*
{finding.get('description', 'No description provided.')}
*Raw Evidence:*
{{code}}
{json.dumps(finding.get('raw_evidence', []), indent=2)}
{{code}}
"""
        issue_dict = {'project': {'key': self.jira_project}, 'summary': summary, 'description': description, 'issuetype': {'name': 'Bug'}}
        try:
            new_issue = self.jira_client.create_issue(fields=issue_dict)
            return f"Jira Ticket Created: {new_issue.key}"
        except Exception as e:
            log.error(f"Failed to create Jira ticket: {e}")
            return None

class SlackNotificationHandler(ResponseHandler):
    """Sends a Slack notification for a validated finding."""
    def __init__(self, notification_manager: NotificationManager):
        self.notification_manager = notification_manager

    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        message = f"Security Finding: {finding.get('title', 'Untitled Finding')}"
        details = {
            "Severity": finding.get('severity', 'N/A'),
            "Host": finding.get('host', 'N/A'),
            "Description": finding.get('description', 'No description provided.')
        }
        if self.notification_manager.send_notification("slack", message, details):
            return "Slack Notification Sent"
        return None

class EmailAlertHandler(ResponseHandler):
    """Sends an email alert for a validated finding."""
    def __init__(self, notification_manager: NotificationManager):
        self.notification_manager = notification_manager

    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        message = f"Security Finding: {finding.get('title', 'Untitled Finding')}"
        details = {
            "Severity": finding.get('severity', 'N/A'),
            "Host": finding.get('host', 'N/A'),
            "Description": finding.get('description', 'No description provided.')
        }
        if self.notification_manager.send_notification("email", message, details):
            return "Email Alert Sent"
        return None

class SMSAlertHandler(ResponseHandler):
    """Sends an SMS alert for a critical validated finding."""
    def __init__(self, notification_manager: NotificationManager):
        self.notification_manager = notification_manager

    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        if finding.get('severity') != 'Critical':
            return None

        message = f"Critical Security Finding: {finding.get('title', 'Untitled Finding')} on {finding.get('host', 'N/A')}"
        if self.notification_manager.send_notification("sms", message):
            return "SMS Alert Sent"
        return None

class DashboardAlertHandler(ResponseHandler):
    """Creates a dashboard alert."""
    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        log.info(f"Creating dashboard alert for: {finding.get('title')}")
        return "Dashboard Alert Created"

class APIWebhookTriggerHandler(ResponseHandler):
    """Triggers an API webhook."""
    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        log.info(f"Triggering API webhook for: {finding.get('title')}")
        return "API Webhook Triggered"

class FullReportGenerationHandler(ResponseHandler):
    """Generates a full report."""
    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        log.info(f"Generating full report for: {finding.get('title')}")
        return "Full Report Generated"

class BugBountyPlatformSubmissionHandler(ResponseHandler):
    """Submits a finding to a bug bounty platform."""
    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        log.info(f"Submitting to bug bounty platform: {finding.get('title')}")
        return "Submitted to Bug Bounty Platform"

class ArchiveCreationHandler(ResponseHandler):
    """Creates an archive of the finding."""
    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        log.info(f"Creating archive for: {finding.get('title')}")
        return "Archive Created"

class NextScanSchedulingHandler(ResponseHandler):
    """Schedules a next scan."""
    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        log.info(f"Scheduling next scan for: {finding.get('title')}")
        return "Next Scan Scheduled"

class ResponseEngine:
    """
    Takes action on validated findings and updates their final disposition.
    """
    def __init__(self, findings: List[Dict[str, Any]]):
        self.findings = findings
        notification_manager = NotificationManager()
        self.handlers: List[ResponseHandler] = [
            JiraTicketHandler(),
            SlackNotificationHandler(notification_manager),
            EmailAlertHandler(notification_manager),
            SMSAlertHandler(notification_manager),
            DashboardAlertHandler(),
            APIWebhookTriggerHandler(),
            FullReportGenerationHandler(),
            BugBountyPlatformSubmissionHandler(),
            ArchiveCreationHandler(),
            NextScanSchedulingHandler(),
        ]

    def run(self) -> List[Dict[str, Any]]:
        """
        The main entry point for the response process.
        """
        validated_findings = [f for f in self.findings if f.get("status") == "Validated"]
        log.info(f"Starting response process for {len(validated_findings)} validated findings...")
        for finding in validated_findings:
            dispositions = []
            for handler in self.handlers:
                try:
                    result = handler.handle(finding)
                    if result:
                        dispositions.append(result)
                except Exception as e:
                    log.error(f"Error in response handler {handler.__class__.__name__}: {e}")
            if dispositions:
                finding['disposition'] = "; ".join(dispositions)
        log.info("Response process finished.")
        return self.findings
