import logging
import os
import json
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, List

# Mock JIRA for now as it's not a core dependency for all users
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
    """
    Creates a Jira ticket for a validated finding.
    """

    def __init__(self):
        self.jira_url = os.getenv("JIRA_URL")
        self.jira_user = os.getenv("JIRA_USERNAME")
        self.jira_token = os.getenv("JIRA_API_TOKEN")
        self.jira_project = os.getenv("JIRA_PROJECT_KEY")
        self.jira_client = None

        if not JIRA:
            log.warning("Jira library not installed. `pip install jira` to use Jira integration.")
            return

        if self.jira_url and self.jira_user and self.jira_token:
            try:
                self.jira_client = JIRA(server=self.jira_url, basic_auth=(self.jira_user, self.jira_token))
                log.info("Jira client initialized successfully.")
            except Exception as e:
                log.error(f"Failed to connect to Jira: {e}")

    def handle(self, finding: Dict[str, Any]):
        if not self.jira_client or not self.jira_project:
            log.debug("Jira integration is not configured. Skipping ticket creation.")
            return

        summary = f"Security Finding: {finding.get('title', 'Untitled Finding')}"
        description = f"""
*Severity:* {finding.get('severity', 'N/A')}
*Confidence:* {finding.get('confidence', 'N/A')}
*Status:* {finding.get('status', 'N/A')}
*Host:* {finding.get('host', 'N/A')}
*Type:* {finding.get('vulnerability_type', 'N/A')}
*Tags:* {', '.join(finding.get('tags', []))}

*Description:*
{finding.get('description', 'No description provided.')}

*Raw Evidence:*
{{code}}
{json.dumps(finding.get('raw_evidence', []), indent=2)}
{{code}}
"""
        # Ensure description is not too long for Jira
        if len(description) > 32767:
            description = description[:32764] + "..."

        issue_dict = {
            'project': {'key': self.jira_project},
            'summary': summary,
            'description': description,
            'issuetype': {'name': 'Bug'},
        }

        try:
            new_issue = self.jira_client.create_issue(fields=issue_dict)
            log.warning(f"Successfully created Jira ticket {new_issue.key} for finding: {summary}")
        except Exception as e:
            log.error(f"Failed to create Jira ticket for '{summary}': {e}")


class SlackAlertingHandler(ResponseHandler):
    """
    Sends a Slack alert for a validated finding.
    """

    def __init__(self):
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    def handle(self, finding: Dict[str, Any]):
        if not self.webhook_url:
            log.debug("Slack webhook URL not configured. Skipping alert.")
            return

        color = {
            "Critical": "#ff0000",
            "High": "#ff4d4d",
            "Medium": "#ffcc00",
            "Low": "#00aaff"
        }.get(finding.get('severity', 'Low'), "#808080")

        message = {
            "attachments": [{
                "color": color,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"🚨 *New Validated Security Finding*"
                        }
                    },
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": finding.get('title', 'Untitled Finding')
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Severity:*\n{finding.get('severity', 'N/A')}"},
                            {"type": "mrkdwn", "text": f"*Host:*\n{finding.get('host', 'N/A')}"},
                            {"type": "mrkdwn", "text": f"*Confidence:*\n{finding.get('confidence', 'N/A')}"},
                            {"type": "mrkdwn", "text": f"*Type:*\n{finding.get('vulnerability_type', 'N/A')}"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Description:*\n{finding.get('description', 'No description provided.')}"
                        }
                    }
                ]
            }]
        }

        try:
            response = requests.post(self.webhook_url, json=message, timeout=10)
            if response.status_code == 200:
                log.info(f"Successfully sent Slack alert for finding: {finding.get('title')}")
            else:
                log.error(f"Failed to send Slack alert. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            log.error(f"Failed to send Slack alert: {e}")


class ResponseEngine:
    """
    The Response Engine is responsible for taking action on validated findings,
    such as creating tickets or sending alerts.
    """

    def __init__(self, findings: List[Dict[str, Any]]):
        self.findings = findings
        self.handlers = [
            JiraTicketHandler(),
            SlackAlertingHandler()
        ]

    def run(self):
        """
        The main entry point for the response process. It only acts on findings
        that have been explicitly validated.
        """
        validated_findings = [f for f in self.findings if f.get("status") == "Validated"]
        log.info(f"Starting response process for {len(validated_findings)} validated findings...")

        for finding in validated_findings:
            log.info(f"Dispatching response handlers for finding: {finding.get('title')}")
            for handler in self.handlers:
                try:
                    handler.handle(finding)
                except Exception as e:
                    log.error(f"Error in response handler {handler.__class__.__name__} for finding {finding.get('id')}: {e}")

        log.info("Response process finished.")
