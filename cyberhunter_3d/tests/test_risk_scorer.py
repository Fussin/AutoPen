import pytest
from cyberhunter_3d.core.scoring.risk_scorer import calculate_risk

def test_calculate_risk_critical():
    """Tests risk calculation for a critical vulnerability."""
    cve_list = [
        {"cve": {"id": "CVE-2021-1234", "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 9.8}}]}}}
    ]
    risk = calculate_risk(cve_list)
    assert risk["risk_level"] == "Critical"
    assert risk["cvss_score"] == 9.8
    assert risk["cve_ids"] == ["CVE-2021-1234"]

def test_calculate_risk_high():
    """Tests risk calculation for a high-risk vulnerability."""
    cve_list = [
        {"cve": {"id": "CVE-2021-1234", "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 8.0}}]}}}
    ]
    risk = calculate_risk(cve_list)
    assert risk["risk_level"] == "High"
    assert risk["cvss_score"] == 8.0

def test_calculate_risk_medium():
    """Tests risk calculation for a medium-risk vulnerability."""
    cve_list = [
        {"cve": {"id": "CVE-2021-1234", "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 5.5}}]}}}
    ]
    risk = calculate_risk(cve_list)
    assert risk["risk_level"] == "Medium"
    assert risk["cvss_score"] == 5.5

def test_calculate_risk_low():
    """Tests risk calculation for a low-risk vulnerability."""
    cve_list = [
        {"cve": {"id": "CVE-2021-1234", "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 2.5}}]}}}
    ]
    risk = calculate_risk(cve_list)
    assert risk["risk_level"] == "Low"
    assert risk["cvss_score"] == 2.5

def test_calculate_risk_none():
    """Tests risk calculation with no CVEs."""
    risk = calculate_risk([])
    assert risk["risk_level"] == "None"
    assert risk["cvss_score"] == 0.0
    assert risk["cve_ids"] == []

def test_calculate_risk_with_kev():
    """Tests that the known_exploits flag is correctly set."""
    cve_list = [
        {"cve": {"id": "CVE-2021-1234", "cisaExploitAdd": "2021-11-03"}}
    ]
    risk = calculate_risk(cve_list)
    assert risk["known_exploits"] is True

def test_calculate_risk_without_kev():
    """Tests that the known_exploits flag is correctly set when no KEV."""
    cve_list = [
        {"cve": {"id": "CVE-2021-1234"}}
    ]
    risk = calculate_risk(cve_list)
    assert risk["known_exploits"] is False
