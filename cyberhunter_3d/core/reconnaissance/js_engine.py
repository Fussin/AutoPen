import subprocess
import tempfile
import os
import concurrent.futures
from typing import Set, List

from .utils import load_config, get_logger, run_command

config = load_config()
logger = get_logger(__name__)

def run_js_enumeration(live_hosts: Set[str]) -> Set[str]:
    """
    Runs JS/Code analysis tools in parallel.
    """
    logger.info(f"Starting JS/Code analysis for {len(live_hosts)} live hosts...")

    if not live_hosts:
        logger.warning("No live hosts to analyze. Skipping JS/Code analysis engine.")
        return set()

    all_results = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # LinkFinder
        for host in live_hosts:
            command = ['python3', config['tools']['linkfinder'], '-i', host, '-o', 'cli']
            future = executor.submit(run_command, command, host)
            try:
                results = future.result()
                if results:
                    logger.info(f"Found {len(results)} endpoints in JS files for {host}")
                    all_results.update(results)
            except Exception as exc:
                logger.error(f"LinkFinder generated an exception for {host}: {exc}")

        # Nuclei - js-secrets
        # Create a temporary file with the live hosts
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            host_filename = tmp_file.name
            for host in live_hosts:
                tmp_file.write(f"{host}\n")

        command = [config['tools']['nuclei'], '-l', host_filename, '-t', 'technologies/javascript/js-secrets.yaml', '-o', '{output_file}', '-silent']
        future = executor.submit(run_command, command, "") # domain is not used here
        try:
            results = future.result()
            if results:
                logger.info(f"Found {len(results)} secrets in JS files.")
                all_results.update(results)
        except Exception as exc:
            logger.error(f"Nuclei js-secrets generated an exception: {exc}")
        finally:
            os.remove(host_filename)


    logger.info(f"Total unique findings from JS/Code analysis: {len(all_results)}")
    return all_results

def run_github_dorking(subdomains: Set[str]) -> List[str]:
    """
    Performs GitHub dorking to find sensitive information.
    """
    logger.info(f"Starting GitHub dorking for {len(subdomains)} subdomains...")

    if not subdomains:
        logger.warning("No subdomains to dork. Skipping GitHub dorking.")
        return []

    # We need a file with dorks.
    dorks_file = config['wordlists']['github_dorks']
    if not os.path.exists(dorks_file):
        logger.error(f"Dorks file not found at {dorks_file}. Skipping GitHub dorking.")
        return []

    # Create a temporary file with the subdomains to use as orgs
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        orgs_filename = tmp_file.name
        for sub in subdomains:
            # We can treat each subdomain as a potential organization name
            if '.' in sub:
                org = sub.split('.')[-2] # a.b.c -> b
                tmp_file.write(f"{org}\n")

    findings = []
    try:
        gh_dork_command = [
            'python3', config['tools']['gh_dork'],
            '-d', dorks_file,
            '-of', orgs_filename,
            '-o', 'gh_dork_results'
        ]
        subprocess.run(gh_dork_command)

        # The results are saved to files in the 'gh_dork_results' directory.
        # We can parse these files to get the findings.
        if os.path.exists('gh_dork_results'):
            for filename in os.listdir('gh_dork_results'):
                with open(os.path.join('gh_dork_results', filename), 'r') as f:
                    findings.extend(f.readlines())

    except FileNotFoundError:
        logger.error("Error: 'gh-dork.py' not found. Please ensure it is installed.")
    except Exception as e:
        logger.error(f"An error occurred during GitHub dorking: {e}")
    finally:
        os.remove(orgs_filename)
        if os.path.exists('gh_dork_results'):
            import shutil
            shutil.rmtree('gh_dork_results')

    logger.info(f"Found {len(findings)} potential findings from GitHub dorking.")
    return findings
