import subprocess
import tempfile
import os
import re
import concurrent.futures
from typing import Set, List

from .utils import load_config, get_logger, run_command

config = load_config()
logger = get_logger(__name__)

def generate_custom_wordlist(subdomains: Set[str]) -> str:
    """
    Generates a custom wordlist from a set of known subdomains.
    """
    custom_words = set()
    for sub in subdomains:
        # Remove the root domain to focus on the subdomain parts
        # This is a simple approach; a more robust one would use a library like tldextract
        parts = sub.split('.')
        if len(parts) > 2:
            subdomain_part = '.'.join(parts[:-2])
            for word in subdomain_part.replace('-', '.').split('.'):
                if word and not word.isnumeric():
                    custom_words.add(word)

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        wordlist_filename = tmp_file.name
        for word in custom_words:
            tmp_file.write(f"{word}\n")

    return wordlist_filename

def run_permutation_enumeration(domain: str, known_subdomains: Set[str]) -> Set[str]:
    """
    Runs permutation-based subdomain enumeration tools in parallel.
    """
    logger.info(f"Starting permutation enumeration for: {domain}")

    if not known_subdomains:
        logger.warning("No known subdomains to permute. Skipping permutation engine.")
        return set()

    # Generate a custom wordlist from the known subdomains
    custom_wordlist_filename = generate_custom_wordlist(known_subdomains)
    logger.info(f"Generated custom wordlist at: {custom_wordlist_filename}")

    # Create a temporary file with the known subdomains
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        subdomain_filename = tmp_file.name
        for sub in known_subdomains:
            tmp_file.write(f"{sub}\n")

    # For permutation, we also need a wordlist.
    generic_wordlist = config['wordlists']['dns_bruteforce']

    # Combine the wordlists
    combined_wordlist_filename = f"combined_wordlist_{domain}.txt"
    with open(combined_wordlist_filename, 'w') as outfile:
        for wordlist in [generic_wordlist, custom_wordlist_filename]:
            if os.path.exists(wordlist):
                with open(wordlist, 'r') as infile:
                    outfile.write(infile.read())

    commands = [
        [config['tools']['dnsgen'], subdomain_filename, '-w', combined_wordlist_filename, '-o', '{output_file}'],
        [config['tools']['gotator'], '-sub', subdomain_filename, '-perm', combined_wordlist_filename, '-depth', '2', '-mindup', '>', '{output_file}']
    ]

    all_subdomains = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
        future_to_command = {executor.submit(run_command, cmd, domain, combined_wordlist_filename): cmd for cmd in commands}
        for future in concurrent.futures.as_completed(future_to_command):
            command = future_to_command[future]
            try:
                subdomains = future.result()
                logger.info(f"Found {len(subdomains)} subdomains with {' '.join(command)}")
                all_subdomains.update(subdomains)
            except Exception as exc:
                logger.error(f"'{' '.join(command)}' generated an exception: {exc}")

    os.remove(subdomain_filename)
    os.remove(custom_wordlist_filename)
    os.remove(combined_wordlist_filename)
    logger.info(f"Total unique permuted subdomains found: {len(all_subdomains)}")
    return all_subdomains
