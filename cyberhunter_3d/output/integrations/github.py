# GitHub integration for CyberHunter 3D.
import requests

def map_risk_to_labels(risk_level: str) -> list[str]:
    """Maps risk level to GitHub labels."""
    labels = ["bug"]
    risk_map = {
        "Critical": "P1-Critical",
        "High": "P2-High",
        "Medium": "P3-Medium",
        "Low": "P4-Low",
    }
    if risk_level in risk_map:
        labels.append(risk_map[risk_level])
    return labels

def search_for_issue(summary: str, config: dict, headers: dict) -> bool:
    """Searches for an existing GitHub issue with a given title."""
    owner = config.get('owner')
    repo = config.get('repo')
    search_url = "https://api.github.com/search/issues"

    query = f'repo:{owner}/{repo} is:issue in:title "{summary}"'
    params = {'q': query}

    try:
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        if response.json().get('total_count', 0) > 0:
            print(f"Duplicate GitHub issue found for: {summary}")
            return True
    except requests.exceptions.RequestException as e:
        print(f"Error searching for GitHub issue: {e}")
        return True # Fail safe
    return False

def create_github_issue(vulnerability: dict, config: dict):
    """
    Creates a GitHub issue from a vulnerability finding, checking for duplicates first.
    """
    token = config.get('token')
    owner = config.get('owner')
    repo = config.get('repo')

    if not all([token, owner, repo]):
        print("Error: GitHub configuration is incomplete.")
        return

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    summary = vulnerability.get('name')

    if search_for_issue(summary, config, headers):
        return

    url = f"https://api.github.com/repos/{owner}/{repo}/issues"

    labels = map_risk_to_labels(vulnerability.get('risk_level'))

    payload = {
        "title": summary,
        "body": vulnerability.get('description'),
        "labels": labels
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"GitHub issue created successfully: {response.json()['html_url']}")
    except requests.exceptions.RequestException as e:
        print(f"Error creating GitHub issue: {e}")
