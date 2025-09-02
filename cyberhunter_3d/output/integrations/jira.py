# Jira integration for CyberHunter 3D.
import requests
from requests.auth import HTTPBasicAuth

def map_risk_to_priority(risk_level: str) -> str:
    """Maps risk level to Jira priority."""
    mapping = {
        "Critical": "Highest",
        "High": "High",
        "Medium": "Medium",
        "Low": "Low",
    }
    return mapping.get(risk_level, "Lowest")

def search_for_issue(summary: str, config: dict, auth) -> bool:
    """Searches for an existing Jira issue with a given summary."""
    jira_url = config.get('url')
    project_key = config.get('project_key')
    search_url = f"{jira_url}/rest/api/2/search"

    headers = {"Accept": "application/json"}
    jql = f'project = "{project_key}" AND summary ~ "{summary}"'
    params = {'jql': jql, 'fields': 'summary'}

    try:
        response = requests.get(search_url, headers=headers, params=params, auth=auth)
        response.raise_for_status()
        if response.json().get('total', 0) > 0:
            print(f"Duplicate Jira issue found for: {summary}")
            return True
    except requests.exceptions.RequestException as e:
        print(f"Error searching for Jira issue: {e}")
        # Fail safe: if search fails, better to not create a duplicate
        return True
    return False

def create_jira_issue(vulnerability: dict, config: dict):
    """
    Creates a Jira issue from a vulnerability finding, checking for duplicates first.
    """
    jira_url = config.get('url')
    jira_user = config.get('user')
    jira_token = config.get('token')
    project_key = config.get('project_key')

    if not all([jira_url, jira_user, jira_token, project_key]):
        print("Error: Jira configuration is incomplete.")
        return

    auth = HTTPBasicAuth(jira_user, jira_token)
    summary = vulnerability.get('name')

    if search_for_issue(summary, config, auth):
        return

    url = f"{jira_url}/rest/api/2/issue"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    priority = map_risk_to_priority(vulnerability.get('risk_level'))

    payload = {
        "fields": {
            "project": {
                "key": project_key
            },
            "summary": summary,
            "description": vulnerability.get('description'),
            "issuetype": {
                "name": "Bug"
            },
            "priority": {
                "name": priority
            }
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, auth=auth)
        response.raise_for_status()
        print(f"Jira issue created successfully: {response.json()['key']}")
    except requests.exceptions.RequestException as e:
        print(f"Error creating Jira issue: {e}")
