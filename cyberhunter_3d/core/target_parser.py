import re
from typing import List, Tuple

# Regex to identify different target types
# This regex for domain names is a simplified version for this use case.
# It allows for subdomains and standard TLDs.
DOMAIN_REGEX = re.compile(
    r'^(?:[a-zA-Z0-9]'  # First character of the domain
    r'(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)'  # Subdomains
    r'+[a-zA-Z]{2,6}$'  # TLD
)

# Regex for wildcard domains (e.g., *.example.com)
WILDCARD_DOMAIN_REGEX = re.compile(
    r'^\*\.((?:[a-zA-Z0-9]'
    r'(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)'
    r'+[a-zA-Z]{2,6})$'
)

# Regex for IP addresses (IPv4) that validates the 0-255 range for each octet.
IP_ADDRESS_REGEX = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
)

# Regex for CIDR notation that validates the 0-255 range for the IP part.
CIDR_REGEX = re.compile(
    r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/([0-9]|[1-2][0-9]|3[0-2])$'
)

# Regex for ASN identifiers (e.g., AS15169, as1234, 1234)
ASN_REGEX = re.compile(r'^(?:as|AS)?(\d+)$')


def parse_single_target(target_str: str) -> Tuple[str, str]:
    """
    Parses a single target string and identifies its type.

    Returns a tuple of (normalized_value, type).
    'type' can be 'domain', 'wildcard_domain', 'ip_address', 'cidr', or 'unknown'.
    """
    target_str = target_str.strip().lower()

    if not target_str:
        return None, 'empty'

    # Check for wildcard first, as it's more specific than domain
    wildcard_match = WILDCARD_DOMAIN_REGEX.match(target_str)
    if wildcard_match:
        # For wildcards, we normalize by storing the base domain
        base_domain = wildcard_match.group(1)
        return base_domain, 'wildcard_domain'

    if IP_ADDRESS_REGEX.match(target_str):
        # Further validation for valid IP ranges (0-255) can be added here
        # For now, the regex is a good first pass.
        return target_str, 'ip_address'

    if CIDR_REGEX.match(target_str):
        return target_str, 'cidr'

    asn_match = ASN_REGEX.match(target_str)
    if asn_match:
        # For ASNs, we normalize by storing just the number
        asn_number = asn_match.group(1)
        return asn_number, 'asn'

    if DOMAIN_REGEX.match(target_str):
        return target_str, 'domain'

    return target_str, 'unknown'


def parse_targets(raw_targets: List[str]) -> List[Tuple[str, str]]:
    """
    Parses a list of raw target strings into a list of (value, type) tuples.
    Filters out empty or invalid entries.
    """
    parsed_list = []
    for target_str in raw_targets:
        normalized_value, target_type = parse_single_target(target_str)
        if target_type not in ['unknown', 'empty']:
            parsed_list.append((normalized_value, target_type))

    return parsed_list
