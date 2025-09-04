import asyncio
import json
from typing import List, Dict, Set
import aiodns
from src.common.plugin_loader import load_plugins
from src.common.config import load_config

async def resolve_subdomain(resolver, subdomain):
    """Helper function to resolve a single subdomain and handle errors."""
    try:
        await resolver.query(subdomain, 'A')
        return subdomain
    except aiodns.error.DNSError:
        return None

async def resolve_subdomains_async(subdomains: List[str]) -> Set[str]:
    """
    Resolves a list of subdomains asynchronously.
    """
    resolver = aiodns.DNSResolver()
    tasks = [resolve_subdomain(resolver, sub) for sub in subdomains]
    results = await asyncio.gather(*tasks)
    return {res for res in results if res is not None}

async def run_recon_phase(domain: str):
    """
    Orchestrates the reconnaissance phase.
    """
    print(f"Starting reconnaissance phase for {domain}...")

    # 1. Load config
    config = load_config()

    # 2. Load enabled recon plugins
    recon_plugins = load_plugins("src/plugins/recon", config)

    subdomain_enum_plugins = [p for p in recon_plugins if p.name() in ["subfinder", "amass", "fierce", "dnsenum", "theharvester"]]
    httpx_plugin = next((p for p in recon_plugins if p.name() == "httpx"), None)
    subjack_plugin = next((p for p in recon_plugins if p.name() == "subjack"), None)
    whatweb_plugin = next((p for p in recon_plugins if p.name() == "whatweb"), None)

    # 3. Run subdomain enumeration plugins
    all_subdomains: Set[str] = set()
    all_findings: List[Dict] = []

    for plugin in subdomain_enum_plugins:
        findings = plugin.run([domain])
        all_findings.extend(findings)
        for finding in findings:
            if finding.get("vuln", {}).get("name") == "Subdomain Discovered":
                all_subdomains.add(finding["evidence"]["poc"])

    with open("outputs/subdomains_all.txt", "w") as f:
        for sub in sorted(list(all_subdomains)):
            f.write(f"{sub}\n")
    print(f"Found {len(all_subdomains)} unique subdomains.")

    # 4. DNS Resolution
    print("Starting DNS resolution...")
    resolved_subdomains = await resolve_subdomains_async(list(all_subdomains))
    with open("outputs/subdomains_resolved.txt", "w") as f:
        for sub in sorted(list(resolved_subdomains)):
            f.write(f"{sub}\n")
    print(f"DNS resolution complete. {len(resolved_subdomains)} subdomains resolved.")

    # 5. Live Host Detection with HTTPx
    live_hosts = []
    if httpx_plugin and resolved_subdomains:
        httpx_findings = httpx_plugin.run(list(resolved_subdomains))
        all_findings.extend(httpx_findings)
        for finding in httpx_findings:
            if finding.get("vuln", {}).get("name") == "Live Host Detected":
                live_hosts.append(finding["target"])

    with open("outputs/subdomains_alive.txt", "w") as f:
        for host in sorted(live_hosts):
            f.write(f"{host}\n")

    dead_hosts = resolved_subdomains - set(live_hosts)
    with open("outputs/subdomains_dead.txt", "w") as f:
        for host in sorted(list(dead_hosts)):
            f.write(f"{host}\n")
    print(f"Found {len(live_hosts)} live hosts.")

    # 6. Subdomain Takeover Check with Subjack
    if subjack_plugin and live_hosts:
        takeover_findings = subjack_plugin.run(live_hosts)
        all_findings.extend(takeover_findings)
        with open("outputs/takeover_findings.json", "w") as f:
            json.dump(takeover_findings, f, indent=4)
    print("Subdomain takeover check complete.")

    # 7. Tech ID Enrichment with WhatWeb
    if whatweb_plugin and live_hosts:
        whatweb_findings = whatweb_plugin.run(live_hosts)
        all_findings.extend(whatweb_findings)
    print("Technology enrichment complete.")

    print("Reconnaissance phase complete.")
    return all_findings

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        asyncio.run(run_recon_phase(sys.argv[1]))
    else:
        print("Usage: python src/phases/recon.py <domain>")
