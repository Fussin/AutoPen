from typing import Set
import re
from cyberhunter_3d.utils.logger import setup_logger

# Common uninteresting subdomains to filter out.
# This list can be expanded over time.
FALSE_POSITIVE_PATTERNS = [
    r'^autodiscover\.',
    r'^cpanel\.',
    r'^webmail\.',
    r'^ftp\.',
    r'^mail\.',
    r'^smtp\.',
    r'^imap\.',
    r'^pop\.',
    r'^ns[0-9]+\.',
    r'^www\.', # Often not interesting for recon, but can be debatable.
]

def filter_false_positives(subdomains: Set[str], logger) -> Set[str]:
    """
    Filters out likely false positive subdomains using a list of regex patterns.
    This is a rule-based approach that serves as a practical implementation
    of the AI noise filter.
    """
    logger.info("AI Noise Filter: Applying rule-based filtering for common false positives...")

    filtered_subdomains = set()
    removed_count = 0

    for sub in subdomains:
        is_false_positive = False
        for pattern in FALSE_POSITIVE_PATTERNS:
            if re.search(pattern, sub):
                is_false_positive = True
                removed_count += 1
                logger.debug(f"Filtered out subdomain '{sub}' due to pattern: {pattern}")
                break

        if not is_false_positive:
            filtered_subdomains.add(sub)

    logger.info(f"AI Noise Filter: Removed {removed_count} potential false positive subdomains.")
    return filtered_subdomains
