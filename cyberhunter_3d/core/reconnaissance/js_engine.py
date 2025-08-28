import subprocess
import tempfile
import os
import re
import concurrent.futures
from typing import Set, List
import shutil

from .utils import load_config, get_logger

config = load_config()
logger = get_logger(__name__)

def extract_subdomains_from_text(text: str, domain: str) -> Set[str]:
    """
    Uses regex to find potential subdomains for a given domain within a block of text.
    """
    # This regex is designed to find domain-like patterns.
    generic_domain_regex = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+")
    potential_domains = generic_domain_regex.findall(text)

    # Filter for subdomains of the target domain
    subdomains = {
        host.lower() for host in potential_domains if host.lower().endswith(f".{domain}") and host.lower() != domain
    }
    return subdomains

def run_github_dorking(domain: str) -> str:
    """
    Performs GitHub dorking to find sensitive information related to a domain.
    Returns the raw text output of the findings.
    """
    logger.info(f"Starting GitHub dorking for domain: {domain}")
    dorks_file = config['wordlists'].get('github_dorks')
    gh_dork_tool = config['tools'].get('gh_dork')

    if not all([dorks_file, gh_dork_tool]):
        logger.warning("GitHub dorks file or gh_dork tool not configured. Skipping.")
        return ""

    if not os.path.exists(dorks_file):
        logger.error(f"Dorks file not found at {dorks_file}. Skipping GitHub dorking.")
        return ""

    # Use the domain name itself as the organization for the search
    org_name = domain.split('.')[0]
    output_dir = f"gh_dork_results_{org_name}"

    try:
        gh_dork_command = [
            'python3', gh_dork_tool,
            '-d', dorks_file,
            '-o', org_name, # Use single org search
            '-n', output_dir
        ]
        subprocess.run(gh_dork_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        findings = []
        if os.path.exists(output_dir):
            for filename in os.listdir(output_dir):
                with open(os.path.join(output_dir, filename), 'r', errors='ignore') as f:
                    findings.append(f.read())

        return "\n".join(findings)

    except Exception as e:
        logger.error(f"An error occurred during GitHub dorking: {e}")
        return ""
    finally:
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)

def run_js_and_code_analysis(domain: str, live_hosts: Set[str]) -> Set[str]:
    """
    Crawls live hosts for JS files, searches code repositories,
    and extracts subdomains from the findings.
    """
    logger.info(f"Starting JS & Code analysis for {len(live_hosts)} live hosts.")
    if not live_hosts:
        logger.warning("No live hosts to analyze. Skipping JS/Code analysis engine.")
        return set()

    all_raw_text = []

    # 1. Crawl for JS files and other links with Katana
    logger.info("Crawling hosts with Katana...")
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as hosts_file:
        hosts_filename = hosts_file.name
        for host in live_hosts:
            hosts_file.write(f"{host}\n")

    with tempfile.NamedTemporaryFile(mode='r', delete=False, suffix=".txt") as katana_output:
        katana_output_filename = katana_output.name

    try:
        katana_cmd = [
            config['tools']['katana'],
            '-l', hosts_filename,
            '-silent',
            '-o', katana_output_filename
        ]
        subprocess.run(katana_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        all_raw_text.append(katana_output.read())
        logger.info("Katana crawl completed.")
    except Exception as e:
        logger.error(f"Katana execution failed: {e}")
    finally:
        os.remove(hosts_filename)
        os.remove(katana_output_filename)

    # 2. Run GitHub Dorking
    github_findings = run_github_dorking(domain)
    if github_findings:
        all_raw_text.append(github_findings)
        logger.info("GitHub dorking completed.")

    # 3. Aggregate all text and extract subdomains
    logger.info("Extracting subdomains from all collected text...")
    combined_text = "\n".join(all_raw_text)

    extracted_subdomains = extract_subdomains_from_text(combined_text, domain)

    logger.info(f"Found {len(extracted_subdomains)} unique subdomains from JS & Code analysis.")
    return extracted_subdomains
