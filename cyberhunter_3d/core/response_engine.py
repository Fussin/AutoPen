import logging
import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from flask import current_app
import zipfile
import requests
from .notifications.notification_manager import NotificationManager
from ..reporting.pdf_generator import generate_pdf_report
from ..utils.file_utils import get_results_dir
from ..web.models import Alert, Scan, Target, db

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
        message = f"New finding: {finding.get('title')}"
        alert = Alert(message=message)

        if 'alerts' not in finding:
            finding['alerts'] = []
        finding['alerts'].append(alert)

        log.info(f"Creating dashboard alert for: {finding.get('title')}")
        return "Dashboard Alert Created"

class APIWebhookTriggerHandler(ResponseHandler):
    """Triggers an API webhook."""
    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        webhook_url = os.getenv("API_WEBHOOK_URL")
        if not webhook_url:
            log.info("API_WEBHOOK_URL not set. Skipping webhook trigger.")
            return None

        try:
            response = requests.post(webhook_url, json=finding)
            response.raise_for_status()
            log.info(f"Successfully triggered webhook for finding: {finding.get('title')}")
            return "API Webhook Triggered"
        except requests.exceptions.RequestException as e:
            log.error(f"Failed to trigger webhook for finding {finding.get('title')}: {e}")
            return None

class FullReportGenerationHandler(ResponseHandler):
    """Generates a full report."""
    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        scan_id = finding.get("scan_id")
        domain = finding.get("target_domain")
        if not scan_id or not domain:
            log.error("Cannot generate report: scan_id or domain not found in finding.")
            return None

        pdf_path = generate_pdf_report(scan_id, domain, current_app._get_current_object())
        if pdf_path:
            return f"Full Report Generated at {pdf_path}"
        return None

class BugBountyPlatformSubmissionHandler(ResponseHandler):
    """Submits a finding to a bug bounty platform."""
    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        scan_id = finding.get("scan_id")
        domain = finding.get("target_domain")
        if not scan_id or not domain:
            log.error("Cannot create submission: scan_id or domain not found in finding.")
            return None

        results_dir = get_results_dir(domain, scan_id)
        submission_path = os.path.join(results_dir, f"bug_bounty_submission_{finding.get('title', 'untitled').replace(' ', '_')}.json")

        try:
            with open(submission_path, 'w') as f:
                json.dump(finding, f, indent=4, default=str)
            log.info(f"Successfully created bug bounty submission at {submission_path}")
            return f"Bug bounty submission created at {submission_path}"
        except Exception as e:
            log.error(f"Failed to create bug bounty submission for finding {finding.get('title')}: {e}")
            return None

class ArchiveCreationHandler(ResponseHandler):
    """Creates an archive of the finding."""
    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        scan_id = finding.get("scan_id")
        domain = finding.get("target_domain")
        if not scan_id or not domain:
            log.error("Cannot create archive: scan_id or domain not found in finding.")
            return None

        results_dir = get_results_dir(domain, scan_id)
        archive_path = os.path.join(results_dir, f"scan_archive_{scan_id}.zip")

        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(results_dir):
                    for file in files:
                        # Don't add previous archives to the new one
                        if file.endswith('.zip'):
                            continue
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, results_dir))

            log.info(f"Successfully created archive at {archive_path}")
            return f"Archive created at {archive_path}"
        except Exception as e:
            log.error(f"Failed to create archive for scan {scan_id}: {e}")
            return None

class NextScanSchedulingHandler(ResponseHandler):
    """Schedules a next scan."""
    def handle(self, finding: Dict[str, Any]) -> Optional[str]:
        scan_id = finding.get("scan_id")
        if not scan_id:
            log.error("Cannot schedule next scan: scan_id not found in finding.")
            return None

        try:
            # Get the current scan to find the user_id and targets
            current_scan = Scan.query.get(scan_id)
            if not current_scan:
                log.error(f"Cannot schedule next scan: Scan with id {scan_id} not found.")
                return None

            # Create a new scan with the same targets
            new_scan = Scan(
                user_id=current_scan.user_id,
                status='SCHEDULED',
                name=f"Follow-up to scan {current_scan.id}",
                in_scope_rules=current_scan.in_scope_rules,
                out_of_scope_rules=current_scan.out_of_scope_rules
            )
            db.session.add(new_scan)
            db.session.flush() # To get the new_scan.id

            for target in current_scan.targets:
                new_target = Target(value=target.value, type=target.type, scan_id=new_scan.id)
                db.session.add(new_target)

            db.session.commit()
            log.info(f"Successfully scheduled next scan with ID: {new_scan.id}")
            return f"Next scan scheduled with ID: {new_scan.id}"
        except Exception as e:
            log.error(f"Failed to schedule next scan for finding {finding.get('title')}: {e}")
            db.session.rollback()
            return None

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
