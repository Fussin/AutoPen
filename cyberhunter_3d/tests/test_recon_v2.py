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

@patch('cyberhunter_3d.core.reconnaissance.subdomain_takeover.os.path.exists', return_value=True)
@patch('cyberhunter_3d.core.reconnaissance.subdomain_takeover.subprocess.Popen')
def test_run_takeover_scan(mock_popen, mock_exists):
    """
    Test the subdomain takeover scan functionality.
    """
    from cyberhunter_3d.core.reconnaissance.subdomain_takeover import run_takeover_scan

    # Mock the Popen process and its output
    process_mock = mock_popen.return_value
    mock_output = [
        '{"template-id":"aws-s3-takeover","info":{"name":"AWS S3 Subdomain Takeover","author":"geeknik","severity":"high"},"host":"sub.example.com"}',
        '{"template-id":"another-takeover","info":{"name":"Another Takeover","author":"tester","severity":"critical"},"host":"vuln.example.com"}'
    ]
    process_mock.stdout = mock_output
    process_mock.communicate.return_value = ('', '') # stdout, stderr
    process_mock.returncode = 0

    test_subdomains = ["sub.example.com", "vuln.example.com", "safe.example.com"]
    results = run_takeover_scan(test_subdomains)

    # Assertions
    assert len(results) == 2
    assert results[0]['template-id'] == 'aws-s3-takeover'
    assert results[1]['host'] == 'vuln.example.com'

    # Check if nuclei was called correctly
    mock_popen.assert_called_once()
    args, kwargs = mock_popen.call_args
    command = args[0]
    assert 'nuclei' in command[0]
    assert '-t' in command
    assert 'takeovers' in command
    assert '-json' in command
