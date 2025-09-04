from typing import List, Dict, Tuple

def calculate_risk(cve_list: List[Dict]) -> Dict:
    """
    Calculates the overall risk for a host based on a list of its CVEs.

    Returns a dictionary with:
    - cve_ids: A list of CVE IDs.
    - cvss_score: The highest CVSS v3 score found.
    - risk_level: The corresponding risk level (Critical, High, Medium, Low, None).
    - known_exploits: A boolean indicating if any of the CVEs are in CISA's KEV catalog.
    """
    if not cve_list:
        return {
            "cve_ids": [],
            "cvss_score": 0.0,
            "risk_level": "None",
            "known_exploits": False,
        }

    cve_ids = []
    highest_cvss_score = 0.0
    has_kev = False

    for cve_data in cve_list:
        cve = cve_data.get('cve', {})
        cve_id = cve.get('id')
        if cve_id:
            cve_ids.append(cve_id)

        # Check for KEV (Known Exploited Vulnerabilities)
        if cve.get('cisaExploitAdd'):
            has_kev = True

        # Find the highest CVSS v3.1 score
        metrics = cve.get('metrics', {})
        if 'cvssMetricV31' in metrics:
            for metric in metrics['cvssMetricV31']:
                cvss_data = metric.get('cvssData', {})
                base_score = cvss_data.get('baseScore', 0.0)
                if base_score > highest_cvss_score:
                    highest_cvss_score = base_score

    # Map CVSS score to risk level
    risk_level = "None"
    if highest_cvss_score >= 9.0:
        risk_level = "Critical"
    elif highest_cvss_score >= 7.0:
        risk_level = "High"
    elif highest_cvss_score >= 4.0:
        risk_level = "Medium"
    elif highest_cvss_score > 0.0:
        risk_level = "Low"

    return {
        "cve_ids": cve_ids,
        "cvss_score": highest_cvss_score,
        "risk_level": risk_level,
        "known_exploits": has_kev,
    }
