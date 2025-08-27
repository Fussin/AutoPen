import pytest
import os
import json
from unittest.mock import patch
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2

from cyberhunter_3d.core.reconnaissance.utils import load_config

config = load_config()

@pytest.mark.slow
def test_full_recon_pipeline():
    """
    Slow integration test that runs the full V2 recon pipeline.
    """
    domain = "example.com"
    assets = enumerate_subdomains_v2(domain)
    assert assets is not None
    assert os.path.exists(config['final_recon_file'])
    with open(config['final_recon_file'], 'r') as f:
        data = json.load(f)
    assert 'domain' in data

    # Teardown
    if os.path.exists(config['recon_output_dir']):
        import shutil
        shutil.rmtree(config['recon_output_dir'])

@patch('subprocess.run')
def test_passive_engine_runs(mock_run):
    """
    A faster test that only runs the passive engine.
    """
    from cyberhunter_3d.core.reconnaissance.passive_engine import run_passive_enumeration
    domain = "example.com"
    subdomains = run_passive_enumeration(domain)
    assert isinstance(subdomains, set)
    mock_run.assert_called()
