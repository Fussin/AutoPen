import os
import json
import logging
from typing import Dict, Any

log = logging.getLogger(__name__)

def get_results_dir(domain: str, scan_id: int) -> str:
    """Creates and returns the path to the results directory for a scan."""
    base_dir = "recon_results"
    results_dir = os.path.join(base_dir, f"{domain.replace('.', '_')}_{scan_id}")
    os.makedirs(results_dir, exist_ok=True)
    return results_dir

def save_to_json(filename: str, data: Dict[str, Any], results_dir: str) -> str:
    """Saves a dictionary to a JSON file in the specified directory."""
    filepath = os.path.join(results_dir, filename)
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4, default=str)
        log.info(f"Successfully saved results to {filepath}")
        return filepath
    except Exception as e:
        log.error(f"Error saving data to {filepath}: {e}")
        return ""

def create_scan_results_structure(base_dir: str):
    """
    Creates the directory and file structure for the scan results.
    """
    log.info(f"Creating scan results structure in {base_dir}")

    structure = {
        "Scan Results Database": {
            "Subdomain Results": [
                "Subdomain.txt",
                "subdomains_alive.txt",
                "subdomains_dead.txt",
                "subdomain_metadata.json"
            ],
            "URL Discovery Results": [
                "Way_kat.txt",
                "alive_domain.txt",
                "dead_domain.txt",
                "api_endpoints.txt",
                "interesting_params.txt"
            ],
            "Vulnerability Findings": [
                "critical_vulns.json",
                "xss_findings.txt",
                "sqli_results.txt",
                "sensitive_exposure.txt",
                "vulnerability_summary.json"
            ],
            "Reports": [
                "executive_report.pdf",
                "technical_details.html",
                "remediation_guide.docx",
                "raw_data_export.json"
            ]
        }
    }

    for root, content in structure.items():
        root_path = os.path.join(base_dir, root)
        os.makedirs(root_path, exist_ok=True)

        if isinstance(content, dict):
            for subdir, files in content.items():
                subdir_path = os.path.join(root_path, subdir)
                os.makedirs(subdir_path, exist_ok=True)
                for file in files:
                    file_path = os.path.join(subdir_path, file)
                    with open(file_path, 'w') as f:
                        pass
    log.info("Scan results structure created successfully.")
