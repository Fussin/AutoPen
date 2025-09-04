import asyncio
import json
import argparse
from src.phases.recon import run_recon_phase
from src.phases.urls import run_urls_phase
from src.phases.vuln import run_vuln_phase
from src.phases.network import run_network_phase
from src.phases.osint import run_osint_phase
from src.common.reporting import generate_html_report

async def main():
    """
    Main pipeline controller.
    """
    parser = argparse.ArgumentParser(description="Autonomous Pentesting Pipeline")
    parser.add_argument("domain", help="The root domain to target.")
    args = parser.parse_args()

    print(f"Starting pipeline for domain: {args.domain}")

    # --- Phase 1: Reconnaissance ---
    recon_findings = await run_recon_phase(args.domain)

    # Extract live hosts for the next phases
    live_hosts = []
    for finding in recon_findings:
        if finding.get("tool") == "httpx" and finding.get("vuln", {}).get("name") == "Live Host Detected":
            live_hosts.append(finding["target"])

    # --- Phase 2: URL Discovery ---
    # We can run this on the root domain, or on all discovered subdomains.
    # For now, let's just run it on the root domain.
    url_findings = await run_urls_phase(args.domain)

    # Extract alive URLs for the vuln phase
    alive_urls = []
    with open("outputs/alive_domain.txt", "r") as f:
        alive_urls = [line.strip() for line in f.readlines()]

    # --- Phase 3: Vulnerability Scanning ---
    vuln_targets = {"urls": alive_urls}
    vuln_findings = await run_vuln_phase(vuln_targets)

    # --- Phase 4: Network Scanning ---
    # We can get the IP addresses from the recon phase.
    # For now, let's assume the domain resolves to a single IP.
    network_targets = [args.domain]
    network_findings = await run_network_phase(network_targets)

    # --- Phase 5: OSINT ---
    # This phase can be run with various inputs.
    osint_targets = {"usernames": ["admin", "root", args.domain.split('.')[0]]}
    osint_findings, _ = await run_osint_phase(osint_targets)

    # --- Aggregation and Reporting ---
    all_findings = recon_findings + url_findings + vuln_findings + network_findings + osint_findings

    with open("outputs/findings_aggregated.json", "w") as f:
        json.dump(all_findings, f, indent=4)

    generate_html_report(all_findings, "reports/final_report.html")

    print("Pipeline finished.")

if __name__ == "__main__":
    asyncio.run(main())
