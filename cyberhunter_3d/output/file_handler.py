import os
import json
from typing import Dict, Any
from . import utils

def generate_output_files(results: Dict[str, Any], output_dir: str):
    """
    Generates all the output files from the aggregated results.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    hosts = results.get('hosts', [])

    # Generate Subdomain.txt
    subdomains = utils.format_subdomains(hosts)
    with open(os.path.join(output_dir, 'Subdomain.txt'), 'w') as f:
        for subdomain in subdomains:
            f.write(f"{subdomain}\n")

    # Generate alive_domain.txt
    alive_domains = utils.format_alive_domains(hosts)
    with open(os.path.join(output_dir, 'alive_domain.txt'), 'w') as f:
        for domain in alive_domains:
            f.write(f"{domain}\n")

    # Generate dead_domain.txt
    dead_domains = utils.format_dead_domains(hosts)
    with open(os.path.join(output_dir, 'dead_domain.txt'), 'w') as f:
        for domain in dead_domains:
            f.write(f"{domain}\n")

    # Generate Way_kat.txt
    url_discovery = results.get('url_discovery', {})
    all_urls = []
    all_urls.extend(url_discovery.get('alive_urls', []))
    all_urls.extend(url_discovery.get('redirect_urls', []))
    with open(os.path.join(output_dir, 'Way_kat.txt'), 'w') as f:
        for url in all_urls:
            f.write(f"{url}\n")

    # Generate all_vulns.json
    vulnerabilities = results.get('vulnerabilities', [])
    with open(os.path.join(output_dir, 'all_vulns.json'), 'w') as f:
        json.dump(vulnerabilities, f, indent=4)
