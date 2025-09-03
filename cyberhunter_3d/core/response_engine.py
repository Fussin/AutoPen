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
    Takes action on validated findings and updates their final disposition.
    """
    def __init__(self, findings: List[Dict[str, Any]]):
        self.findings = findings
        self.handlers: List[ResponseHandler] = [JiraTicketHandler()]

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
