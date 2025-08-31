import logging
import requests
import json

log = logging.getLogger(__name__)

def send_slack_alert(webhook_url: str, finding: dict):
    """
    Sends a formatted alert to a Slack webhook for a critical vulnerability.

    Args:
        webhook_url: The Slack Incoming Webhook URL.
        finding: The vulnerability finding dictionary.
    """
    if not webhook_url:
        log.debug("Slack webhook URL not configured. Skipping alert.")
        return

    try:
        # Extract key information from the finding
        name = finding.get("info", {}).get("name", "N/A")
        severity = finding.get("info", {}).get("severity", "N/A").upper()
        host = finding.get("host", "N/A")
        matched_at = finding.get("matched-at", host) # Use matched-at if available, otherwise host
        template_id = finding.get("template-id", "N/A")

        # Construct a Slack Block Kit message
        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f":warning: Critical Vulnerability Detected: {name}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Severity:*\n`{severity}`"},
                        {"type": "mrkdwn", "text": f"*Template:*\n`{template_id}`"},
                        {"type": "mrkdwn", "text": f"*Host:*\n`{host}`"},
                        {"type": "mrkdwn", "text": f"*Matched At:*\n`{matched_at}`"}
                    ]
                },
                {
                    "type": "divider"
                }
            ]
        }

        headers = {'Content-Type': 'application/json'}
        response = requests.post(webhook_url, data=json.dumps(payload), headers=headers, timeout=10)

        if response.status_code == 200:
            log.info(f"Successfully sent Slack alert for finding: {name}")
        else:
            log.error(f"Failed to send Slack alert. Status: {response.status_code}, Response: {response.text}")

    except Exception as e:
        log.error(f"An error occurred while sending Slack alert: {e}")
