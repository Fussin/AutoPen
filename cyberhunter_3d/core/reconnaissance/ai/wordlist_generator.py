from typing import Set, List
import itertools

# A dictionary of common tech terms and their variations.
TECH_SYNONYMS = {
    "dev": ["development", "dev", "develop"],
    "prod": ["production", "prod", "live"],
    "stag": ["staging", "stage", "stg"],
    "test": ["testing", "test", "tst"],
    "uat": ["uat", "user-acceptance-testing"],
    "admin": ["administrator", "admin", "adm"],
    "api": ["api", "gateway", "gw"],
    "db": ["database", "db", "sql", "mysql", "postgres"],
    "git": ["git", "gitlab", "github", "gitea"],
    "ci": ["ci", "jenkins", "bamboo", "teamcity"],
    "cd": ["cd", "argo", "spinnaker"],
}

def generate_ai_wordlist(seed_words: Set[str]) -> Set[str]:
    """
    Generates a new wordlist based on permutations and combinations of seed words
    and common technical terms. This is a more advanced rule-based generator.
    """
    new_words = set()

    # Add synonyms for seed words if they match any key in our dictionary
    for word in list(seed_words):
        for key, synonyms in TECH_SYNONYMS.items():
            if key in word:
                new_words.update(synonyms)

    # Combine seed words with common tech terms
    all_tech_words = set(itertools.chain.from_iterable(TECH_SYNONYMS.values()))

    # Combine with separators
    separators = ["-", "_", ".", ""]
    for word1 in seed_words:
        for word2 in all_tech_words:
            for sep in separators:
                new_words.add(f"{word1}{sep}{word2}")
                new_words.add(f"{word2}{sep}{word1}")

    # Add some common prefixes and suffixes as well
    prefixes = ["dev", "stage", "api", "test", "uat", "prod"]
    suffixes = ["-dev", "-staging", "-uat", "-test", "-prod"]
    for word in seed_words:
        for prefix in prefixes:
            new_words.add(f"{prefix}{word}")
            new_words.add(f"{prefix}.{word}")
        for suffix in suffixes:
            new_words.add(f"{word}{suffix}")

    return new_words
