import pytest
from cyberhunter_3d.core.reconnaissance.ai.wordlist_generator import generate_ai_wordlist

def test_generate_ai_wordlist():
    """
    Tests that the generate_ai_wordlist function generates a reasonable set of
    new words based on the seed words and predefined tech terms.
    """
    seed_words = {"corp"}

    generated_words = generate_ai_wordlist(seed_words)

    # Check for some expected generated words
    assert "corp-dev" in generated_words
    assert "dev-corp" in generated_words
    assert "corp.admin" in generated_words
    assert "admin.corp" in generated_words
    assert "devcorp" in generated_words

def test_generate_ai_wordlist_with_synonyms():
    """
    Tests that the wordlist generator correctly expands seed words that
    are also keys in the TECH_SYNONYMS dictionary.
    """
    seed_words = {"dev"}

    generated_words = generate_ai_wordlist(seed_words)

    # Check that synonyms are added
    assert "development" in generated_words
    assert "develop" in generated_words

    # Check for combinations of seed words with synonyms of other tech terms
    assert "dev-database" in generated_words
