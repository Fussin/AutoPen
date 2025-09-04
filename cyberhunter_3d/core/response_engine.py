import logging
import os
import json
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

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

class NotificationLoggerHandler(ResponseHandler):
    """A simple handler that logs a finding to a file."""
    def __init__(self, log_file: str = "notifications.log"):
        self.log_file = log_file

    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        try:
            message = (
                f"--- New Triaged Finding ---\n"
                f"Title: {finding.get('title', 'N/A')}\n"
                f"Severity: {finding.get('severity', 'N/A')}\n"
                f"Confidence: {finding.get('confidence', 'N/A')}\n"
                f"Host: {finding.get('host', 'N/A')}\n"
                f"Description: {finding.get('description', 'N/A')}\n"
                f"---------------------------\n\n"
            )
            with open(self.log_file, "a") as f:
                f.write(message)
            log.info(f"Logged finding to {self.log_file}")
            return f"Logged to {self.log_file}"
        except Exception as e:
            log.error(f"Failed to write to notification log {self.log_file}: {e}")
            return None

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

class ResponseEngine:
    """
    Takes action on validated findings based on event types.
    """

    def __init__(self):
        notification_manager = NotificationManager()

        # Initialize all handlers
        self.all_handlers = {
            "jira": JiraTicketHandler(),
            "slack": SlackNotificationHandler(notification_manager),
            "email": EmailAlertHandler(notification_manager),
            "sms": SMSAlertHandler(notification_manager),
            "dashboard": DashboardAlertHandler(),
            "webhook": APIWebhookTriggerHandler(),
            "report": FullReportGenerationHandler(),
            "bug_bounty": BugBountyPlatformSubmissionHandler(),
            "archive": ArchiveCreationHandler(),
            "schedule": NextScanSchedulingHandler(),
        }

        # Map event types to handlers
        self.event_handlers = {
            'CRITICAL_FINDING_DETECTED': [
                self.all_handlers["slack"],
                self.all_handlers["email"],
                self.all_handlers["sms"],
                self.all_handlers["dashboard"],
                self.all_handlers["jira"],
            ],
            'SCAN_MILESTONE_REACHED': [
                self.all_handlers["slack"],
                self.all_handlers["dashboard"],
                self.all_handlers["webhook"],
            ],
            'SCAN_COMPLETION': [
                self.all_handlers["report"],
                self.all_handlers["bug_bounty"],
                self.all_handlers["archive"],
                self.all_handlers["schedule"],
            ]
        }

    def run(self, findings: List[Dict[str, Any]], event_type: str) -> List[Dict[str, Any]]:
        """
        The main entry point for the response process.
        """
        handlers_for_event = self.event_handlers.get(event_type)
        if not handlers_for_event:
            log.warning(f"No handlers found for event type: {event_type}")
            return findings

        log.info(f"Running response process for event '{event_type}' on {len(findings)} findings...")
        for finding in findings:

    def __init__(self, findings: List[Dict[str, Any]]):
        self.findings = findings
        self.handlers: List[ResponseHandler] = [
            NotificationLoggerHandler(),
            JiraTicketHandler()
        ]

    def run(self) -> List[Dict[str, Any]]:
        """
        The main entry point for the response process.
        """
        triaged_findings = [f for f in self.findings if f.get("status") == "Triaged"]
        log.info(f"Starting response process for {len(triaged_findings)} triaged findings...")
        for finding in triaged_findings:

            dispositions = []
            for handler in handlers_for_event:
                try:
                    result = handler.handle(finding)
                    if result:
                        dispositions.append(result)
                except Exception as e:
                    log.error(f"Error in response handler {handler.__class__.__name__}: {e}")

            if dispositions:
                if 'disposition' not in finding or not finding['disposition']:
                    finding['disposition'] = ""

                new_dispositions = "; ".join(dispositions)
                if finding['disposition']:
                    finding['disposition'] += f"; {new_dispositions}"
                else:
                    finding['disposition'] = new_dispositions

        log.info(f"Response process for event '{event_type}' finished.")
        return findings
