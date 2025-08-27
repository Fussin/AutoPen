import pytest
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains

def test_enumerate_subdomains_integration():
    """
    Integration test for the enumerate_subdomains function.
    This test runs the full pipeline with a real domain.
    It checks if the function returns a list of assets without crashing.
    """
    domain = "example.com"
    assets = enumerate_subdomains(domain)

    # We expect to get a list of assets
    assert isinstance(assets, list)

    # We can't know for sure how many subdomains will be found,
    # but we can check that if any are found, they have the correct structure.
    if assets:
        for asset in assets:
            assert 'type' in asset
            assert asset['type'] == 'subdomain'
            assert 'value' in asset
            assert 'status' in asset
            assert asset['status'] in ['live', 'dead']
            if asset['status'] == 'live':
                assert 'url' in asset
