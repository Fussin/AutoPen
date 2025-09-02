# GitHub integration for CyberHunter 3D.
import requests

def create_github_issue(vulnerability: dict, config: dict):
    """
    Creates a GitHub issue from a vulnerability finding.
    """
    token = config.get('token')
    owner = config.get('owner')
    repo = config.get('repo')

    if not all([token, owner, repo]):
        print("Error: GitHub configuration is incomplete.")
        return

    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    payload = {
        "title": vulnerability.get('name'),
        "body": vulnerability.get('description')
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"GitHub issue created successfully: {response.json()['html_url']}")
    except requests.exceptions.RequestException as e:
        print(f"Error creating GitHub issue: {e}")
