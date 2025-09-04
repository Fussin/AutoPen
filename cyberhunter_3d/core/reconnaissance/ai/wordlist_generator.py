import logging
import re
from typing import List, Set
from collections import Counter

log = logging.getLogger(__name__)

def generate_intelligent_wordlist(keywords: List[str]) -> List[str]:
    """
    Generates a prioritized wordlist from a list of keywords.
    """
    log.info(f"Generating intelligent wordlist from {len(keywords)} keywords.")

    prefixes = ["dev", "stage", "uat", "test", "demo", "api", "vpn"]
    suffixes = ["-dev", "-stage", "-uat", "-test", "-demo", "-api", "-vpn"]

    wordlist = []
    for keyword in keywords:
        wordlist.append(keyword)
        for prefix in prefixes:
            wordlist.append(f"{prefix}-{keyword}")
            wordlist.append(f"{prefix}{keyword}")
        for suffix in suffixes:
            wordlist.append(f"{keyword}{suffix}")

    final_wordlist = sorted(list(set(wordlist)))
    log.info(f"Generated wordlist with {len(final_wordlist)} unique words.")
    return final_wordlist

def extract_keywords_from_subdomains(subdomains: List[str]) -> List[str]:
    """
    Extracts meaningful keywords from a list of subdomains.
    """
    log.info(f"Extracting keywords from {len(subdomains)} subdomains.")

    words = []
    for sub in subdomains:
        parts = sub.split('.')
        if len(parts) > 2:
            subdomain_part = '.'.join(parts[:-2])
            words.extend(re.split(r'[\.\-_]', subdomain_part))

    common_words = {'www', 'mail', 'ftp', 'cpanel', 'webmail', 'webdisk'}
    filtered_words = [word for word in words if word and word not in common_words and len(word) > 2 and not word.isnumeric()]

    word_counts = Counter(filtered_words)
    most_common_words = [word for word, count in word_counts.most_common(20)]

    log.info(f"Extracted {len(most_common_words)} keywords: {most_common_words}")
    return most_common_words
