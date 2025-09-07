from cyberhunter_3d.web.models import db, Vulnerability

SEVERITY_TO_PRIORITY = {
    'critical': 1,
    'high': 2,
    'medium': 3,
    'low': 4,
    'info': 5,
    'unknown': 6,
}

def prioritize_vulnerabilities(scan_id: int):
    """
    Analyzes and assigns a priority to all vulnerabilities for a given scan.

    :param scan_id: The ID of the scan to analyze.
    """
    print(f"PRIORITIZATION: Starting prioritization for scan {scan_id}...")

    vulnerabilities = Vulnerability.query.filter_by(scan_id=scan_id).all()
    if not vulnerabilities:
        print(f"PRIORITIZATION: No vulnerabilities found for scan {scan_id}.")
        return

    updated_count = 0
    for vuln in vulnerabilities:
        # Assign priority based on severity
        # We use .get() to default to the lowest priority if severity is unknown
        priority = SEVERITY_TO_PRIORITY.get(vuln.severity.lower(), 6)

        if vuln.priority != priority:
            vuln.priority = priority
            updated_count += 1

    if updated_count > 0:
        db.session.commit()

    print(f"PRIORITIZATION: Finished. Updated priority for {updated_count} vulnerabilities.")
