import os
import importlib
import asyncio
from typing import List, Dict, Set
from src.common.plugin_loader import load_plugins
from src.common.config import load_config
from src.plugins.recon.httpx import HttpxPlugin

async def run_urls_phase(domain: str):
    """
    Orchestrates the URL discovery phase.
    """
    print(f"Starting URL discovery phase for {domain}...")

    # 1. Load config
    config = load_config()

    # 2. Load enabled URL discovery plugins
    url_plugins = load_plugins("src/plugins/urls", config)

    # 3. Run URL discovery plugins
    all_urls: Set[str] = set()
    all_findings: List[Dict] = []

    for plugin in url_plugins:
        findings = plugin.run([domain])
        all_findings.extend(findings)
        for finding in findings:
            if finding.get("vuln", {}).get("name") == "URL Discovered":
                all_urls.add(finding["evidence"]["poc"])

    # 4. Merge and dedup
    master_url_list = sorted(list(all_urls))
    with open("outputs/way_kat.txt", "w") as f:
        for url in master_url_list:
            f.write(f"{url}\n")
    print(f"Found {len(master_url_list)} unique URLs.")

    # 5. Parameter discovery (placeholder)
    with open("outputs/parameters_extracted.txt", "w") as f:
        f.write("# Placeholder for extracted parameters\n")
    print("Parameter discovery complete (placeholder).")

    # 6. Response code bucketing with HTTPx
    httpx_plugin = HttpxPlugin()
    if httpx_plugin.check_dependencies() and master_url_list:
        httpx_findings = httpx_plugin.run(master_url_list)

        alive_urls = []
        dead_urls = []
        redirect_urls = []

        url_status_map = {}
        for finding in httpx_findings:
            if finding.get("vuln", {}).get("name") == "Live Host Detected":
                url = finding["target"]
                try:
                    status_code = int(finding["evidence"].get("snippet", "").split("Status: ")[1].split(",")[0])
                    url_status_map[url] = status_code
                except (IndexError, ValueError):
                    pass

        for url in master_url_list:
            status = url_status_map.get(url)
            if status:
                if 200 <= status < 300:
                    alive_urls.append(url)
                elif 300 <= status < 400:
                    redirect_urls.append(url)
                else:
                    dead_urls.append(url)
            else:
                dead_urls.append(url)

        with open("outputs/alive_domain.txt", "w") as f:
            for url in sorted(alive_urls):
                f.write(f"{url}\n")
        with open("outputs/dead_domain.txt", "w") as f:
            for url in sorted(dead_urls):
                f.write(f"{url}\n")
        with open("outputs/redirect_30x.txt", "w") as f:
            for url in sorted(redirect_urls):
                f.write(f"{url}\n")
        print("Response code bucketing complete.")

    print("URL discovery phase complete.")
    return all_findings

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        asyncio.run(run_urls_phase(sys.argv[1]))
    else:
        print("Usage: python src/phases/urls.py <domain>")
