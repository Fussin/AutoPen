import yaml
import os
from cyberhunter_3d.web.models import Finding, Scan
from cyberhunter_3d.core.notifications import send_slack_notification

def load_triage_rules():
    """Loads triage rules from the YAML file."""
    rules_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'triage_rules.yaml')
    with open(rules_path, 'r') as f:
        return yaml.safe_load(f)

def triage_finding(finding: Finding, rules: list):
    """
    Applies triage rules to a single finding.
    Returns True if the finding was triaged, False otherwise.
    """
    if finding.is_triaged:
        return False

    for rule_item in rules:
        rule = rule_item['rule']
        for keyword in rule['keywords']:
            if keyword.lower() in finding.title.lower() or keyword.lower() in finding.description.lower():
                finding.severity = rule['severity']
                finding.confidence = rule['confidence']
                finding.is_triaged = True

                # Check if a notification should be sent
                if finding.severity == "Critical" and finding.confidence == "High":
                    workspace = finding.scan.workspace
                    if workspace.slack_webhook_url:
                        message = (
                            f"🚨 *Critical Finding Alert* in Workspace: *{workspace.name}*\n"
                            f"> *Title:* {finding.title}\n"
                            f"> *Severity:* {finding.severity}\n"
                            f"> *Confidence:* {finding.confidence}\n"
                            f"A new high-confidence, critical vulnerability has been automatically triaged."
                        )
                        send_slack_notification(workspace.slack_webhook_url, message)
                return True
    return False

def run_triage_on_scan(scan_id, db):
    """
    Runs the triage engine on all untriaged findings for a given scan.
    """
    rules = load_triage_rules()
    findings = Finding.query.filter_by(scan_id=scan_id, is_triaged=False).all()

    for finding in findings:
        triage_finding(finding, rules)

    db.session.commit()
    print(f"Triage complete for scan {scan_id}. {len(findings)} findings processed.")
