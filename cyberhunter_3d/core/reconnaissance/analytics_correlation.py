import subprocess
import tempfile
import os
import re
from typing import List, Set, Dict

# Regex for Google Analytics IDs (both old and new formats)
GA_ID_REGEX = re.compile(r'(UA-\d{4,9}-\d{1,4}|G-[A-Z0-9]+)', re.IGNORECASE)

def _find_analytics_ids_for_domain(domain: str) -> Set[str]:
    """
    Uses gospider to find analytics IDs on a single domain.
    """
    ids = set()
    print(f"Searching for analytics IDs on {domain} with gospider...")
    try:
        # gospider -s <domain> -c 10 -d 1 --other-source
        # We want to look for "other sources" which is where it finds analytics IDs
        command = ['gospider', '-s', domain, '-c', '10', '-d', '1', '--other-source']
        result = subprocess.run(command, capture_output=True, text=True, check=False) # check=False as it can return non-zero on success

        output = result.stdout
        if output:
            ids.update(GA_ID_REGEX.findall(output))

    except FileNotFoundError:
        print(f"Error: 'gospider' not found. Please ensure it is installed.")
    except Exception as e:
        print(f"An error occurred while running gospider on {domain}: {e}")

    return ids

def _find_domains_for_analytics_id(analytics_id: str) -> Set[str]:
    """
    Uses gau to find other domains that share the same analytics ID.
    """
    domains = set()
    print(f"Searching for domains sharing analytics ID {analytics_id} with gau...")
    try:
        # gau --subs <analytics_id>
        command = ['gau', '--subs', analytics_id]
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        output = result.stdout
        if output:
            # The output of gau is a list of URLs. We need to parse the domain from them.
            for url in output.strip().splitlines():
                # A simple regex to extract domain from URL
                domain_match = re.search(r'https?://([^/]+)', url)
                if domain_match:
                    domains.add(domain_match.group(1))

    except FileNotFoundError:
        print(f"Error: 'gau' not found. Please ensure it is installed.")
    except Exception as e:
        print(f"An error occurred while running gau for {analytics_id}: {e}")

    return domains

def find_related_domains_by_analytics(domains: List[str]) -> Set[str]:
    """
    Orchestrates the process of finding related domains by analytics IDs.

    :param domains: A list of domain strings to investigate.
    :return: A set of new, related domain strings.
    """
    all_analytics_ids = set()

    # Phase 1: Find all unique analytics IDs from the seed domains
    for domain in domains:
        ids = _find_analytics_ids_for_domain(domain)
        if ids:
            print(f"Found IDs on {domain}: {ids}")
            all_analytics_ids.update(ids)

    if not all_analytics_ids:
        print("No analytics IDs found on seed domains. Skipping expansion.")
        return set()

    # Phase 2: Find all domains related to those analytics IDs
    related_domains = set()
    for analytics_id in all_analytics_ids:
        newly_found_domains = _find_domains_for_analytics_id(analytics_id)
        if newly_found_domains:
            print(f"Found {len(newly_found_domains)} domains for ID {analytics_id}")
            related_domains.update(newly_found_domains)

    # Remove the original seed domains from the result set to only return *new* domains
    final_domains = related_domains - set(domains)

    print(f"Analytics expansion finished. Found {len(final_domains)} new related domains.")
    return final_domains

if __name__ == '__main__':
    # For direct testing of this module
    test_domains = ["example.com"] # Replace with a domain known to have GA IDs for live testing
    related = find_related_domains_by_analytics(test_domains)

    if related:
        print("\n--- Found Related Domains ---")
        for domain in sorted(list(related)):
            print(domain)
