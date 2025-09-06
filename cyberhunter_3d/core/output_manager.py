import os
import time
from pathlib import Path

def create_output_directory(scan_id, base_dir="scan_results"):
    """
    Creates the output directory structure for a given scan.
    """
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    scan_dir_name = f"{timestamp}_{scan_id}"
    scan_path = Path(base_dir) / scan_dir_name

    # Create base directory
    scan_path.mkdir(parents=True, exist_ok=True)

    # Define the directory structure
    dirs_to_create = [
        "reconnaissance",
        "discovery",
        "vulnerabilities/critical",
        "vulnerabilities/high",
        "vulnerabilities/medium",
        "vulnerabilities/low",
        "vulnerabilities/informational",
        "network",
        "reports",
        "evidence/screenshots",
        "evidence/poc_videos",
        "evidence/requests_responses"
    ]

    # Create directories
    for d in dirs_to_create:
        (scan_path / d).mkdir(parents=True, exist_ok=True)

    # Define the file structure
    files_to_create = [
        "reconnaissance/Subdomain.txt",
        "reconnaissance/subdomains_alive.txt",
        "reconnaissance/subdomains_dead.txt",
        "reconnaissance/dns_records.json",
        "reconnaissance/technology_stack.json",
        "discovery/Way_kat.txt",
        "discovery/alive_domain.txt",
        "discovery/dead_domain.txt",
        "discovery/api_endpoints.json",
        "discovery/parameters.json",
        "discovery/javascript_files.txt",
        "network/open_ports.json",
        "network/services.json",
        "network/ssl_issues.json",
        "reports/executive_summary.pdf",
        "reports/technical_report.html",
        "reports/vulnerability_details.json",
        "reports/remediation_guide.docx",
        "metadata.json"
    ]

    # Create empty files
    for f in files_to_create:
        (scan_path / f).touch()

    print(f"Output directory created at: {scan_path}")
    return str(scan_path)
