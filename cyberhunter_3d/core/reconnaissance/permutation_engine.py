import subprocess
import tempfile
import os
import re
import concurrent.futures
from typing import Set, List

from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config, run_command
from .ai.wordlist_generator import generate_ai_wordlist

config = load_config()
logger = setup_logger('PermutationEngine', 'permutation.log')

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

    # Add AI-generated words to the custom wordlist
    logger.info("Generating AI-based wordlist for permutations...")
    ai_words = generate_ai_wordlist(custom_words)
    logger.info(f"Generated {len(ai_words)} additional keywords from AI wordlist generator.")
    custom_words.update(ai_words)

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
        future_to_command = {executor.submit(run_command, cmd, domain, logger, combined_wordlist_filename): cmd for cmd in commands}
        for future in concurrent.futures.as_completed(future_to_command):
            command = future_to_command[future]
            try:
                subdomains = future.result()
                logger.info(f"Found {len(subdomains)} subdomains with {' '.join(command)}")
                all_subdomains.update(subdomains)
            except Exception as exc:
                logger.error(f"'{' '.join(command)}' generated an exception: {exc}")

    # Clean up the temporary wordlists and subdomain lists
    os.remove(subdomain_filename)
    os.remove(custom_wordlist_filename)
    os.remove(combined_wordlist_filename)

    logger.info(f"Generated {len(all_subdomains)} potential subdomains from permutations.")

    if not all_subdomains:
        return set()

    # Step 2: Validate all generated permutations with a mass DNS resolver
    logger.info("Starting mass DNS resolution to validate permuted subdomains...")
    validated_subdomains = set()
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as potential_subs_file:
        potential_subs_filename = potential_subs_file.name
        for sub in all_subdomains:
            potential_subs_file.write(f"{sub}\n")

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as validated_subs_file:
        validated_subs_filename = validated_subs_file.name

    try:
        resolvers = config['wordlists']['resolvers']
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
        logger.info(f"Validated {len(validated_subdomains)} live subdomains from permutations.")

    except FileNotFoundError:
        logger.error(f"Error: '{config['tools']['puredns']}' not found. Please ensure it is installed.")
        return set() # Return empty set as permutations are unvalidated
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during puredns validation for permutations: {e}")
        return set() # Return empty set as permutations are unvalidated
    finally:
        os.remove(potential_subs_filename)
        os.remove(validated_subs_filename)

    logger.info(f"Total unique validated permuted subdomains found: {len(validated_subdomains)}")
    return validated_subdomains
