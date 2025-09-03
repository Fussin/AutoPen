import logging
import os
import json
import requests
import smtplib
from email.mime.text import MIMEText
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
    def handle(self, finding: Dict[str, Any]):
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

    def handle(self, finding: Dict[str, Any]):
        if not self.jira_client or not self.jira_project:
            return
        summary = f"Security Finding: {finding.get('title', 'Untitled Finding')}"
        description = f"""
*Severity:* {finding.get('severity', 'N/A')}
*Confidence:* {finding.get('confidence', 'N/A')}
*Host:* {finding.get('host', 'N/A')}
*Description:*
{finding.get('description', 'No description provided.')}
"""
        issue_dict = {'project': {'key': self.jira_project}, 'summary': summary, 'description': description, 'issuetype': {'name': 'Bug'}}
        try:
            new_issue = self.jira_client.create_issue(fields=issue_dict)
            log.info(f"Jira Ticket Created: {new_issue.key}")
        except Exception as e:
            log.error(f"Failed to create Jira ticket: {e}")

class SlackNotificationHandler(ResponseHandler):
    """Sends a notification to a Slack channel for a high-risk finding."""
    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    def handle(self, finding: Dict[str, Any]):
        if not self.webhook_url:
            return

        summary = f"High-Risk Finding: {finding.get('vulnerability_name', finding.get('title', 'Untitled Finding'))}"
        message = {
            "text": summary,
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": ":warning: " + summary}},
                {"type": "section", "fields": [
                    {"type": "mrkdwn", "text": f"*Host:*\n{finding.get('host', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Risk Score:*\n{finding.get('contextual_risk_score', 'N/A')}"}
                ]}
            ]
        }
        try:
            requests.post(self.webhook_url, json=message, timeout=10)
            log.info(f"Slack notification sent for finding: {summary}")
        except requests.RequestException as e:
            log.error(f"Failed to send Slack notification: {e}")

class EmailResponseHandler(ResponseHandler):
    """Sends an email notification for a high-risk finding."""
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASSWORD")
        self.recipient = os.getenv("EMAIL_RECIPIENT")
        self.sender = os.getenv("EMAIL_SENDER", "cyberhunter@example.com")

    def handle(self, finding: Dict[str, Any]):
        if not all([self.smtp_server, self.recipient]):
            return

        summary = f"High-Risk Finding: {finding.get('vulnerability_name', finding.get('title', 'Untitled Finding'))}"
        body = f"A new high-risk security finding has been identified on host {finding.get('host', 'N/A')}: {summary}"
        msg = MIMEText(body)
        msg['Subject'] = summary
        msg['From'] = self.sender
        msg['To'] = self.recipient

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_user and self.smtp_pass:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.sender, [self.recipient], msg.as_string())
            log.info(f"Email notification sent for finding: {summary}")
        except smtplib.SMTPException as e:
            log.error(f"Failed to send email notification: {e}")


class ResponseEngine:
    """
    Takes action on findings based on their risk score.
    """
    def __init__(self, findings: List[Dict[str, Any]], config: Dict[str, Any]):
        self.findings = findings
        self.config = config.get("response_engine", {})
        self.risk_threshold = self.config.get("risk_threshold", 8.0)

        self.handlers: List[ResponseHandler] = []
        if self.config.get("enable_slack_notifications"):
            self.handlers.append(SlackNotificationHandler())
        if self.config.get("enable_email_notifications"):
            self.handlers.append(EmailResponseHandler())
        if self.config.get("enable_jira_tickets"):
            self.handlers.append(JiraTicketHandler())

    def run(self):
        """
        The main entry point for the response process. Triggers handlers for findings
        that exceed the configured risk threshold.
        """
        high_risk_findings = [f for f in self.findings if f.get("contextual_risk_score", 0.0) >= self.risk_threshold]

        log.info(f"Starting response process for {len(high_risk_findings)} high-risk findings...")
        for finding in high_risk_findings:
            for handler in self.handlers:
                try:
                    handler.handle(finding)
                except Exception as e:
                    log.error(f"Error in response handler {handler.__class__.__name__}: {e}")

        log.info("Response process finished.")
