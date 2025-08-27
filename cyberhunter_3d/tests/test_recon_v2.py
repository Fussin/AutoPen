import pytest
import os
import json
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2

@pytest.fixture(scope="module")
def recon_results():
    """
    Fixture to run the V2 recon pipeline once and share the results.
    """
    # Add the go bin directory to the path
    go_path = os.path.join(os.path.expanduser("~"), "go", "bin")
    os.environ["PATH"] = f"{go_path}:{os.environ['PATH']}"

    domain = "example.com"
    assets = enumerate_subdomains_v2(domain)
    yield assets
    # Teardown: clean up the output file
    if os.path.exists('final_recon_data.json'):
        os.remove('final_recon_data.json')
    if os.path.exists('master_subdomains.txt'):
        os.remove('master_subdomains.txt')


def test_recon_v2_runs_without_errors(recon_results):
    """
    Tests that the V2 recon pipeline runs without crashing.
    """
    assert recon_results is not None

def test_final_recon_data_file_is_created():
    """
    Tests that the final_recon_data.json file is created.
    """
    assert os.path.exists('final_recon_data.json')

def test_final_recon_data_has_correct_structure():
    """
    Tests that the final_recon_data.json file has the correct structure.
    """
    with open('final_recon_data.json', 'r') as f:
        data = json.load(f)

    assert 'domain' in data
    assert 'master_subdomains' in data
    assert 'live_hosts' in data
    assert 'screenshots' in data
    assert 'technology_and_ports' in data
    assert 'js_findings' in data
    assert 'cloud_assets' in data
