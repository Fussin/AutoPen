import requests
import json

def send_slack_notification(webhook_url: str, message: str):
    """
    Sends a notification to a Slack webhook.
    """
    if not webhook_url:
        return False

    headers = {'Content-Type': 'application/json'}
    payload = {'text': message}

    try:
        response = requests.post(webhook_url, headers=headers, data=json.dumps(payload), timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error sending Slack notification: {e}")
        return False
