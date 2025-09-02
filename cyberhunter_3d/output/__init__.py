# This file is part of the CyberHunter 3D output module.
import os
from .file_handler import generate_output_files
from .integrations.jira import create_jira_issue
from .integrations.slack import send_slack_notification
from .integrations.github import create_github_issue
from .archive import create_archive

def run_output_pipeline(results: dict, config: dict, output_dir: str):
    """
    Runs the entire output and integration pipeline.
    """
    # Generate output files
    generate_output_files(results, output_dir)

    # Send notifications and create issues
    if config.get('jira'):
        for vuln in results.get('vulnerabilities', []):
            create_jira_issue(vuln, config['jira'])

    if config.get('slack'):
        send_slack_notification("Reconnaissance scan complete.", config['slack'])

    if config.get('github'):
        for vuln in results.get('vulnerabilities', []):
            create_github_issue(vuln, config['github'])

    # Archive the results
    if config.get('archive'):
        archive_path = os.path.join(output_dir, 'archive.zip')
        create_archive(output_dir, archive_path)
