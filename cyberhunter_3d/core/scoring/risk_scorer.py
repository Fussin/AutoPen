from typing import List, Dict, Any, Tuple

# --- Risk Configuration ---
# Weights for different risk factors. These can be tuned.
RISK_WEIGHTS = {
    "cve_critical": 10,
    "cve_high": 7,
    "cve_medium": 4,
    "cve_low": 1,
    "known_exploit": 15,  # High impact for known exploited vulns
    "takeover_risk": 20, # Very high impact
    "open_port_critical": 5, # e.g., SSH, RDP on 0.0.0.0
    "open_port_high": 3,     # e.g., DBs like Mongo, Redis
    "cloud_asset": 2,
    "login_page": 5, # A login page increases exposure
    "admin_panel": 8, # An admin panel is a high-value target
}

# Ports that are often considered high-risk if exposed.
CRITICAL_PORTS = [22, 3389]
HIGH_RISK_PORTS = [27017, 27018, 6379, 3306, 5432]

# --- Main Scoring Function ---
def calculate_host_risk(host_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculates a comprehensive risk score for a single host.

    :param host_data: A dictionary containing all information about a host.
    :return: A dictionary with the calculated risk score, level, and contributing factors.
    """
    total_score = 0
    contributing_factors = []

    # 1. CVE Risk
    cve_list = host_data.get("cves", [])
    if cve_list:
        cve_score, cve_factors = _evaluate_cve_risk(cve_list)
        total_score += cve_score
        contributing_factors.extend(cve_factors)

    # 2. Subdomain Takeover Risk
    if host_data.get("takeover_risk"):
        total_score += RISK_WEIGHTS["takeover_risk"]
        contributing_factors.append({
            "factor": "Subdomain Takeover",
            "details": "Potential for takeover detected.",
            "score": RISK_WEIGHTS["takeover_risk"]
        })

    # 3. Open Port Risk
    open_ports = host_data.get("open_ports", [])
    if open_ports:
        port_score, port_factors = _evaluate_port_risk(open_ports)
        total_score += port_score
        contributing_factors.extend(port_factors)

    # 4. Screenshot Tag Risk
    screenshot_tags = host_data.get("screenshot_tags", [])
    if screenshot_tags:
        tag_score, tag_factors = _evaluate_tag_risk(screenshot_tags)
        total_score += tag_score
        contributing_factors.extend(tag_factors)

    # 5. Cloud Asset Risk
    if host_data.get("cloud_asset"):
        total_score += RISK_WEIGHTS["cloud_asset"]
        contributing_factors.append({
            "factor": "Cloud Asset",
            "details": "Host identified as a cloud asset.",
            "score": RISK_WEIGHTS["cloud_asset"]
        })

    # --- Risk Clustering (Bonus Score for High-Risk Combos) ---
    # Example: A host with a critical CVE and a login page is extra risky.
    has_critical_cve = any(f['details'].startswith("Critical CVE") for f in contributing_factors)
    has_login_page = any(f['factor'] == "Login Page" for f in contributing_factors)
    has_admin_panel = any(f['factor'] == "Admin Panel" for f in contributing_factors)

    if has_critical_cve and (has_login_page or has_admin_panel):
        bonus = 10
        total_score += bonus
        contributing_factors.append({
            "factor": "Risk Cluster",
            "details": "Critical CVE on a host with a login/admin interface.",
            "score": bonus
        })

    # --- Final Score and Level ---
    risk_level = _map_score_to_level(total_score)

    return {
        "total_risk_score": total_score,
        "risk_level": risk_level,
        "contributing_factors": contributing_factors,
    }


# --- Helper Functions ---
def _evaluate_cve_risk(cve_list: List[Dict]) -> Tuple[int, List[Dict]]:
    """Calculates risk score based on a list of CVEs."""
    score = 0
    factors = []
    has_kev = False

    for cve_data in cve_list:
        cve = cve_data.get('cve', {})
        cve_id = cve.get('id', 'N/A')

        # Check for KEV
        if cve.get('cisaExploitAdd') and not has_kev:
            score += RISK_WEIGHTS["known_exploit"]
            factors.append({
                "factor": "Known Exploit",
                "details": f"CVE {cve_id} is in CISA's KEV catalog.",
                "score": RISK_WEIGHTS["known_exploit"]
            })
            has_kev = True # Only add bonus once per host

        # Get CVSS v3.1 score
        highest_cvss = 0.0
        metrics = cve.get('metrics', {})
        if 'cvssMetricV31' in metrics:
            for metric in metrics['cvssMetricV31']:
                cvss_data = metric.get('cvssData', {})
                base_score = cvss_data.get('baseScore', 0.0)
                if base_score > highest_cvss:
                    highest_cvss = base_score

        if highest_cvss >= 9.0:
            score += RISK_WEIGHTS["cve_critical"]
            factors.append({"factor": "CVE", "details": f"Critical CVE ({cve_id})", "score": RISK_WEIGHTS["cve_critical"]})
        elif highest_cvss >= 7.0:
            score += RISK_WEIGHTS["cve_high"]
            factors.append({"factor": "CVE", "details": f"High CVE ({cve_id})", "score": RISK_WEIGHTS["cve_high"]})
        elif highest_cvss >= 4.0:
            score += RISK_WEIGHTS["cve_medium"]
            factors.append({"factor": "CVE", "details": f"Medium CVE ({cve_id})", "score": RISK_WEIGHTS["cve_medium"]})
        elif highest_cvss > 0:
            score += RISK_WEIGHTS["cve_low"]
            factors.append({"factor": "CVE", "details": f"Low CVE ({cve_id})", "score": RISK_WEIGHTS["cve_low"]})

    return score, factors


def _evaluate_port_risk(open_ports: List[int]) -> Tuple[int, List[Dict]]:
    """Calculates risk score based on open ports."""
    score = 0
    factors = []
    for port in open_ports:
        if port in CRITICAL_PORTS:
            score += RISK_WEIGHTS["open_port_critical"]
            factors.append({
                "factor": "Critical Port",
                "details": f"Port {port} is open.",
                "score": RISK_WEIGHTS["open_port_critical"]
            })
        elif port in HIGH_RISK_PORTS:
            score += RISK_WEIGHTS["open_port_high"]
            factors.append({
                "factor": "High-Risk Port",
                "details": f"Port {port} is open.",
                "score": RISK_WEIGHTS["open_port_high"]
            })
    return score, factors

def _evaluate_tag_risk(tags: List[str]) -> Tuple[int, List[Dict]]:
    """Calculates risk score based on screenshot tags."""
    score = 0
    factors = []
    if "login" in tags or "signin" in tags:
        score += RISK_WEIGHTS["login_page"]
        factors.append({"factor": "Login Page", "details": "A login page was identified.", "score": RISK_WEIGHTS["login_page"]})
    if "admin" in tags or "dashboard" in tags:
        score += RISK_WEIGHTS["admin_panel"]
        factors.append({"factor": "Admin Panel", "details": "An admin panel was identified.", "score": RISK_WEIGHTS["admin_panel"]})
    return score, factors


def _map_score_to_level(score: int) -> str:
    """Maps a numerical score to a qualitative risk level."""
    if score >= 40:
        return "Critical"
    elif score >= 25:
        return "High"
    elif score >= 10:
        return "Medium"
    elif score > 0:
        return "Low"
    else:
        return "None"
