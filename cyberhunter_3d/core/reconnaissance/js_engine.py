import subprocess
import tempfile
import os
import re
import concurrent.futures
from typing import Set, List, Dict, Tuple
import shutil
import json
import requests
from playwright.sync_api import sync_playwright

from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config, save_to_json

config = load_config()
logger = setup_logger('JSEngine', 'js_code.log')

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

def extract_secrets_and_endpoints(text: str) -> List[Dict[str, str]]:
    """
    Uses regex to find API keys, secrets, and endpoints in a block of text.
    """
    findings = []

    # Regex for common API keys and secrets
    secret_patterns = {
        "Stripe Live Key": r"sk_live_[0-9a-zA-Z]{24}",
        "Stripe Test Key": r"sk_test_[0-9a-zA-Z]{24}",
        "AWS Access Key": r"AKIA[0-9A-Z]{16}",
        "Google API Key": r"AIza[0-9A-Za-z\\-_]{35}",
        "GitHub Token": r"ghp_[0-9a-zA-Z]{36}",
    }

    # Regex for API endpoints
    endpoint_patterns = {
        "API Endpoint": r"(\/api\/[a-zA-Z0-9_.\-\/]+)"
    }

    for key_type, pattern in secret_patterns.items():
        for match in re.finditer(pattern, text):
            findings.append({
                "type": "secret",
                "key_type": key_type,
                "value": match.group(0),
                "context": text[max(0, match.start()-50):min(len(text), match.end()+50)]
            })

    for endpoint_type, pattern in endpoint_patterns.items():
        for match in re.finditer(pattern, text):
            findings.append({
                "type": "endpoint",
                "endpoint_type": endpoint_type,
                "value": match.group(0),
                "context": text[max(0, match.start()-50):min(len(text), match.end()+50)]
            })

    return findings

def analyze_js_files(katana_output_file: str, domain: str) -> Tuple[Set[str], List[Dict[str, str]]]:
    """
    Analyzes the content of JS files found by Katana to extract subdomains and secrets.
    """
    subdomains = set()
    secrets = []

    # Regex to find JS files in Katana's output
    js_file_regex = re.compile(r'.*\.js$')

    with open(katana_output_file, 'r', errors='ignore') as f:
        for line in f:
            url = line.strip()
            if js_file_regex.match(url):
                try:
                    response = requests.get(url, timeout=5)
                    response.raise_for_status()
                    text_content = response.text

                    # Extract subdomains and secrets from the content
                    subdomains.update(extract_subdomains_from_text(text_content, domain))
                    secrets.extend(extract_secrets_and_endpoints(text_content))

                except requests.exceptions.RequestException as e:
                    logger.warning(f"Could not fetch JS file at {url}: {e}")
                except Exception as e:
                    logger.error(f"Could not analyze JS file at {url}: {e}")

    return subdomains, secrets

def fetch_page_content_with_playwright(url: str) -> str:
    """
    Uses Playwright to fetch the full HTML content of a page after dynamic rendering.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, wait_until='networkidle')
            content = page.content()
            browser.close()
            return content
    except Exception as e:
        logger.error(f"Playwright failed to fetch {url}: {e}")
        return ""

def run_playwright_analysis(live_hosts: Set[str], domain: str) -> Tuple[Set[str], List[Dict[str, str]]]:
    """
    Uses Playwright to analyze live hosts for subdomains and secrets.
    """
    all_subdomains = set()
    all_secrets = []

    logger.info("Starting Playwright analysis...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(fetch_page_content_with_playwright, f"http://{host}"): host for host in live_hosts}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                content = future.result()
                if content:
                    all_subdomains.update(extract_subdomains_from_text(content, domain))
                    all_secrets.extend(extract_secrets_and_endpoints(content))
            except Exception as exc:
                logger.error(f'{url} generated an exception during Playwright analysis: {exc}')

    logger.info(f"Playwright analysis found {len(all_subdomains)} subdomains and {len(all_secrets)} secrets.")
    return all_subdomains, all_secrets

def run_js_and_code_analysis(domain: str, live_hosts: Set[str]) -> Tuple[Set[str], List[Dict[str, str]]]:
    """
    Crawls live hosts for JS files, searches code repositories,
    and extracts subdomains, secrets, and endpoints from the findings.
    """
    logger.info(f"Starting JS & Code analysis for {len(live_hosts)} live hosts.")
    if not live_hosts:
        logger.warning("No live hosts to analyze. Skipping JS/Code analysis engine.")
        return set(), []

    all_raw_text = []
    all_secrets = []
    all_subdomains = set()

    # 1. Deep analysis with Playwright
    playwright_subdomains, playwright_secrets = run_playwright_analysis(live_hosts, domain)
    all_subdomains.update(playwright_subdomains)
    all_secrets.extend(playwright_secrets)

    # 2. Crawl for JS files and other links with Katana
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
            '-o', katana_output_filename,
            '-jc' # Also extract JS inline code
        ]
        subprocess.run(katana_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Analyze the JS files found by Katana
        js_subdomains, js_secrets = analyze_js_files(katana_output_filename, domain)
        all_subdomains.update(js_subdomains)
        all_secrets.extend(js_secrets)

        # Read the raw output for subdomain extraction from non-JS sources
        with open(katana_output_filename, 'r') as f:
            all_raw_text.append(f.read())

        logger.info("Katana crawl completed.")

    except Exception as e:
        logger.error(f"Katana execution failed: {e}")
    finally:
        os.remove(hosts_filename)
        os.remove(katana_output_filename)

    # 3. Run GitHub Dorking
    github_findings = run_github_dorking(domain)
    if github_findings:
        all_raw_text.append(github_findings)
        all_secrets.extend(extract_secrets_and_endpoints(github_findings))
        logger.info("GitHub dorking completed.")

    # 4. Aggregate all text and extract subdomains from raw text
    logger.info("Extracting subdomains from all collected raw text...")
    combined_text = "\n".join(all_raw_text)
    all_subdomains.update(extract_subdomains_from_text(combined_text, domain))

    # 5. Save secrets to a file
    if all_secrets:
        save_to_json(all_secrets, "secrets_and_endpoints.json", logger)
        logger.info(f"Found {len(all_secrets)} secrets and endpoints.")

    logger.info(f"Found {len(all_subdomains)} unique subdomains from JS & Code analysis.")
    return all_subdomains, all_secrets
