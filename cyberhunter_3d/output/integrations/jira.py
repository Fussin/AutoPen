# Jira integration for CyberHunter 3D.
import requests
from requests.auth import HTTPBasicAuth

def create_jira_issue(vulnerability: dict, config: dict):
    """
    Creates a Jira issue from a vulnerability finding.
    """
    jira_url = config.get('url')
    jira_user = config.get('user')
    jira_token = config.get('token')
    project_key = config.get('project_key')

    if not all([jira_url, jira_user, jira_token, project_key]):
        print("Error: Jira configuration is incomplete.")
        return

    url = f"{jira_url}/rest/api/2/issue"
    auth = HTTPBasicAuth(jira_user, jira_token)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = {
        "fields": {
            "project": {
                "key": project_key
            },
            "summary": vulnerability.get('name'),
            "description": vulnerability.get('description'),
            "issuetype": {
                "name": "Bug"
            }
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, auth=auth)
        response.raise_for_status()
        print(f"Jira issue created successfully: {response.json()['key']}")
    except requests.exceptions.RequestException as e:
        print(f"Error creating Jira issue: {e}")
