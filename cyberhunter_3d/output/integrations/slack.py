# Slack integration for CyberHunter 3D.
import requests

def send_slack_notification(message: str, config: dict):
    """
    Sends a notification to Slack.
    """
    webhook_url = config.get('webhook_url')
    if not webhook_url:
        print("Error: Slack webhook URL not configured.")
        return

    payload = {
        "text": message
    }

    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        print("Slack notification sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Slack notification: {e}")
