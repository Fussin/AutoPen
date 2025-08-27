import pytest
import os
import json
import shutil
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.reconnaissance.utils import load_config

config = load_config()

@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_github_dorking')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.find_cloud_assets')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_tech_fingerprinting')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_js_enumeration')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_takeover_scan')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_visual_recon')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.resolve_and_validate')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_permutation_enumeration')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_active_enumeration')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_passive_enumeration')
def test_full_recon_pipeline_mocked(
    mock_passive, mock_active, mock_permute, mock_resolve,
    mock_visual, mock_takeover, mock_js, mock_tech, mock_cloud, mock_github
):
    """
    Fast, mocked integration test that runs the full V2 recon pipeline logic.
    """
    # 1. Setup Mock Return Values
    mock_passive.return_value = {'passive.example.com'}
    mock_active.return_value = {'active.example.com'}
    # Permutation depends on the results of passive and active
    mock_permute.return_value = {'permute.example.com'}
    # Resolve should return a consolidated set of valid domains
    resolved_domains = {'passive.example.com', 'active.example.com', 'permute.example.com'}
    mock_resolve.return_value = resolved_domains
    # Visual recon returns live hosts and a path to screenshots
    live_hosts = ['http://active.example.com', 'http://passive.example.com']
    mock_visual.return_value = (live_hosts, 'recon_results/screenshots')
    # Other scans return their specific findings
    mock_takeover.return_value = [{'template-id': 'test-takeover', 'host': 'active.example.com'}]
    mock_js.return_value = [{'source': 'test_js', 'url': 'http://passive.example.com'}]
    mock_tech.return_value = {'http://active.example.com': {'tech': 'nginx'}}
    mock_cloud.return_value = [{'asset_type': 's3', 'bucket': 'test-bucket.s3.amazonaws.com'}]
    mock_github.return_value = [{'url': 'https://github.com/test/test/blob/main/key.pem'}]

    # 2. Execute the function
    domain = "example.com"
    assets = enumerate_subdomains_v2(domain)

    # 3. Assertions
    # Check that the final asset list is correct
    assert len(assets) == 3
    assert {'type': 'subdomain', 'value': 'active.example.com'} in assets

    # Check that the final JSON report was created and has the correct data
    output_dir = config['recon_output_dir']
    final_recon_file = os.path.join(output_dir, config['final_recon_file'])
    assert os.path.exists(final_recon_file)

    with open(final_recon_file, 'r') as f:
        data = json.load(f)

    assert data['domain'] == domain
    assert set(data['master_subdomains']) == resolved_domains
    assert set(data['live_hosts']) == set(live_hosts)
    assert len(data['subdomain_takeover_vulnerabilities']) == 1
    assert data['subdomain_takeover_vulnerabilities'][0]['host'] == 'active.example.com'
    assert len(data['technology_and_ports']) == 1
    assert data['technology_and_ports']['http://active.example.com']['tech'] == 'nginx'
    assert len(data['cloud_assets']) == 1
    assert data['cloud_assets'][0]['asset_type'] == 's3'

    # Check that the mocked functions were called correctly
    mock_passive.assert_called_once_with(domain)
    mock_active.assert_called_once_with(domain)
    mock_permute.assert_called_once_with(domain, {'passive.example.com', 'active.example.com'})
    mock_resolve.assert_called_once() # Called with the set of all raw domains
    mock_visual.assert_called_once_with(resolved_domains)
    mock_takeover.assert_called_once_with(live_hosts)

    # Teardown
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

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
