from typing import Dict

def calculate_risk_score(finding: Dict, config: Dict) -> float:
    """
    Calculates a risk score for a finding.
    """
    severity_map = {
        "info": 0.1,
        "low": 0.3,
        "medium": 0.5,
        "high": 0.7,
        "critical": 0.9
    }

    vuln = finding.get("vuln", {})
    severity = vuln.get("severity", "info")
    severity_score = severity_map.get(severity, 0.1)

    # Asset criticality
    asset_criticality = 1.0 # Default
    target = finding.get("target")
    for asset in config.get("assets", []):
        if asset.get("name") == target:
            asset_criticality = asset.get("criticality", 1.0)
            break

    # Tool confidence
    tool_confidence = 1.0 # Default
    tool = finding.get("tool")
    tool_config = config.get("plugins", {}).get(tool, {})
    tool_confidence = tool_config.get("confidence", 1.0)

    # Simple scoring algorithm
    risk_score = severity_score * asset_criticality * tool_confidence

    return round(risk_score, 2)

if __name__ == "__main__":
    # Example usage
    sample_finding = {
        "target": "prod.example.com",
        "tool": "nuclei",
        "vuln": {"name": "SQL Injection", "severity": "high"}
    }
    sample_config = {
        "assets": [
            {"name": "prod.example.com", "criticality": 1.5}
        ],
        "plugins": {
            "nuclei": {"confidence": 0.9}
        }
    }
    score = calculate_risk_score(sample_finding, sample_config)
    print(f"Calculated risk score: {score}") # Expected: 0.7 * 1.5 * 0.9 = 0.945 -> 0.95

    sample_finding_2 = {
        "target": "dev.example.com",
        "tool": "subfinder",
        "vuln": {"name": "Subdomain Discovered", "severity": "info"}
    }
    score_2 = calculate_risk_score(sample_finding_2, sample_config)
    print(f"Calculated risk score 2: {score_2}") # Expected: 0.1 * 1.0 * 1.0 = 0.1
