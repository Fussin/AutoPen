import subprocess
import tempfile
import os
import re
import concurrent.futures
from typing import Set, List

from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config, run_command

config = load_config()
logger = setup_logger('ActiveEngine', 'active.log')

def run_active_enumeration(domain: str) -> Set[str]:
    """
    Runs active subdomain enumeration tools in parallel.
    """
    logger.info(f"Starting active enumeration for: {domain}")

    wordlist = config['wordlists']['dns_bruteforce']
    resolvers = config['wordlists']['resolvers']

    commands = [
        [config['tools']['gobuster'], 'dns', '-d', '{domain}', '-w', wordlist, '-o', '{output_file}', '-q'],
        [config['tools']['puredns'], 'bruteforce', wordlist, '{domain}', '-r', resolvers, '-w', '{output_file}'],
        [config['tools']['nmap'], '--script', 'dns-zone-transfer', '-p', '53', '{domain}', '-oN', '{output_file}']
    ]

    all_subdomains = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
        future_to_command = {executor.submit(run_command, cmd, domain, logger, wordlist): cmd for cmd in commands}
        for future in concurrent.futures.as_completed(future_to_command):
            command = future_to_command[future]
            try:
                subdomains = future.result()
                logger.info(f"Found {len(subdomains)} subdomains with {' '.join(command)}")
                all_subdomains.update(subdomains)
            except Exception as exc:
                logger.error(f"'{' '.join(command)}' generated an exception: {exc}")

    logger.info(f"Found {len(all_subdomains)} potential subdomains from initial active enumeration.")

    if not all_subdomains:
        return set()

    # Step 2: Validate all found subdomains with a mass DNS resolver
    logger.info("Starting mass DNS resolution to validate potential subdomains...")
    validated_subdomains = set()
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as potential_subs_file:
        potential_subs_filename = potential_subs_file.name
        for sub in all_subdomains:
            potential_subs_file.write(f"{sub}\n")

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as validated_subs_file:
        validated_subs_filename = validated_subs_file.name

    try:
        puredns_resolve_cmd = [
            config['tools']['puredns'],
            'resolve',
            potential_subs_filename,
            '-r',
            resolvers,
            '-w',
            validated_subs_filename
        ]
        subprocess.run(puredns_resolve_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        with open(validated_subs_filename, 'r') as f:
            for line in f:
                validated_subdomains.add(line.strip())
        logger.info(f"Validated {len(validated_subdomains)} live subdomains.")

    except FileNotFoundError:
        logger.error(f"Error: '{config['tools']['puredns']}' not found. Please ensure it is installed.")
        # Fallback to returning unvalidated subdomains if puredns is not found
        return all_subdomains
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during puredns validation: {e}")
        # Fallback to returning unvalidated subdomains on error
        return all_subdomains
    finally:
        os.remove(potential_subs_filename)
        os.remove(validated_subs_filename)

    logger.info(f"Total unique validated active subdomains found: {len(validated_subdomains)}")
    return validated_subdomains
