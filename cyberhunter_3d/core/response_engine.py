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
    def handle(self, event: Dict[str, Any]) -> Optional[str]:
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

    def handle(self, event: Dict[str, Any]) -> Optional[str]:
        if not self.jira_client or not self.jira_project:
            return None

        # This handler is specific to findings, so we check for a 'finding' type marker.
        if event.get('type') != 'finding':
            return None

        summary = f"Security Finding: {event.get('title', 'Untitled Finding')}"
        description = f"""
*Severity:* {event.get('severity', 'N/A')}
*Confidence:* {event.get('confidence', 'N/A')}
*Host:* {event.get('host', 'N/A')}
*Description:*
{event.get('description', 'No description provided.')}
*Raw Evidence:*
{{code}}
{json.dumps(event.get('raw_evidence', []), indent=2)}
{{code}}
"""
        issue_dict = {'project': {'key': self.jira_project}, 'summary': summary, 'description': description, 'issuetype': {'name': 'Bug'}}
        try:
            new_issue = self.jira_client.create_issue(fields=issue_dict)
            return f"Jira Ticket Created: {new_issue.key}"
        except Exception as e:
            log.error(f"Failed to create Jira ticket: {e}")
            return None

class LogAlertHandler(ResponseHandler):
    """A simple handler that logs an event to the console."""
    def handle(self, event: Dict[str, Any]) -> Optional[str]:
        # This handler is specific to alerts from the monitor
        if event.get('type') != 'alert':
            return None

        title = event.get('title', 'Untitled Event')
        description = event.get('description', 'No description.')
        log.info(f"--- ALERT HANDLER ---")
        log.info(f"Title: {title}")
        log.info(f"Description: {description}")
        log.info(f"Details: {json.dumps(event.get('details', {}))}")
        log.info(f"--------------------")
        return "Logged to console"


class EventEngine:
    """
    Takes action on events (e.g., findings, alerts) using a set of handlers.
    """
    def __init__(self, events: List[Dict[str, Any]]):
        self.events = events
        self.handlers: List[ResponseHandler] = [JiraTicketHandler(), LogAlertHandler()]

    def run(self) -> List[Dict[str, Any]]:
        """
        The main entry point for the event processing.
        """
        log.info(f"Starting event processing for {len(self.events)} events...")
        for event in self.events:
            # Filter for events that should be processed (e.g. validated findings)
            if event.get("status") != "Validated" and event.get("type") == "finding":
                continue

            dispositions = []
            for handler in self.handlers:
                try:
                    result = handler.handle(event)
                    if result:
                        dispositions.append(result)
                except Exception as e:
                    log.error(f"Error in response handler {handler.__class__.__name__}: {e}")
            if dispositions:
                event['disposition'] = "; ".join(dispositions)
        log.info("Event processing finished.")
        return self.events
