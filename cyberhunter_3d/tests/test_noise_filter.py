import pytest
from cyberhunter_3d.core.reconnaissance.ai.noise_filter import filter_false_positives
from cyberhunter_3d.utils.logger import setup_logger

logger = setup_logger('TestNoiseFilter', 'test_noise_filter.log')

def test_filter_false_positives():
    """
    Tests that the filter_false_positives function correctly removes subdomains
    that match the predefined false positive patterns.
    """
    subdomains_to_test = {
        "example.com",
        "test.example.com",
        "cpanel.example.com", # Should be removed
        "www.example.com",    # Should be removed
        "autodiscover.example.com", # Should be removed
        "ftp.example.com",    # Should be removed
        "mail.example.com",   # Should be removed
        "smtp.example.com",   # Should be removed
        "imap.example.com",   # Should be removed
        "pop.example.com",    # Should be removed
        "ns1.example.com",    # Should be removed
        "dev.example.com",
    }

    expected_subdomains = {
        "example.com",
        "test.example.com",
        "dev.example.com",
    }

    filtered = filter_false_positives(subdomains_to_test, logger)

    assert filtered == expected_subdomains

def test_filter_false_positives_no_matches():
    """
    Tests that the filter works correctly when no subdomains should be filtered.
    """
    subdomains_to_test = {
        "example.com",
        "test.example.com",
        "dev.example.com",
        "api.example.com",
    }

    filtered = filter_false_positives(subdomains_to_test, logger)

    assert filtered == subdomains_to_test
