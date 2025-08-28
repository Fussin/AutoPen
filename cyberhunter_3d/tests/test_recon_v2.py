import pytest
import os
import json
import shutil
from unittest.mock import patch, MagicMock, ANY
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.reconnaissance.utils import load_config

config = load_config()

@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.get_asn_for_ips')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.resolve_subdomains_to_ips')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.detect_wildcard_ips')      # for mock_wildcard
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.find_cloud_assets')      # for mock_cloud
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_tech_fingerprinting')# for mock_tech
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_js_and_code_analysis') # for mock_js_code
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_takeover_scan')      # for mock_takeover
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_visual_recon')       # for mock_visual
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.resolve_and_validate')   # for mock_resolve
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_permutation_enumeration')# for mock_permute
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_active_enumeration') # for mock_active
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_passive_enumeration')# for mock_passive
def test_full_recon_pipeline_mocked(
    mock_passive, mock_active, mock_permute, mock_resolve,
    mock_visual, mock_takeover, mock_js_code, mock_tech, mock_cloud, mock_wildcard,
    mock_resolve_ips, mock_get_asn
):
    """
    Fast, mocked integration test that runs the full V2 recon pipeline logic.
    """
    # 1. Setup Mock Return Values
    mock_passive.return_value = {'passive.example.com'}
    mock_active.return_value = {'active.example.com'}
    mock_permute.return_value = {'permute.example.com'}
    mock_js_code.return_value = {'code.example.com'}
    mock_wildcard.return_value = {'1.2.3.4'}
    resolved_domains = {'passive.example.com', 'active.example.com', 'permute.example.com'}
    mock_resolve.return_value = resolved_domains

    # Mock IP and ASN lookups
    mock_ip_map = {'passive.example.com': ['5.5.5.5']}
    mock_resolve_ips.return_value = mock_ip_map
    mock_asn_details = {'5.5.5.5': {'asn': 'AS-TEST', 'name': 'TEST-NET'}}
    mock_get_asn.return_value = mock_asn_details

    live_hosts = ['http://active.example.com', 'http://passive.example.com']
    mock_visual.return_value = (live_hosts, 'recon_results/screenshots')
    mock_takeover.return_value = [{'template-id': 'test-takeover', 'host': 'active.example.com'}]
    mock_tech.return_value = {'http://active.example.com': {'tech': 'nginx'}}
    mock_cloud.return_value = [{'asset_type': 's3', 'bucket': 'test-bucket.s3.amazonaws.com'}]

    # 2. Execute the function
    domain = "example.com"
    recon_data = enumerate_subdomains_v2(domain)

    # 3. Assertions
    data = recon_data
    assert data['domain'] == domain
    # The master list should now include the subdomains found by the code analysis
    assert set(data['master_subdomains']) == resolved_domains.union({'code.example.com'})
    assert 'subdomain_ip_mapping' in data
    assert 'asn_details' in data
    assert data['subdomain_ip_mapping'] == mock_ip_map
    assert data['asn_details'] == mock_asn_details


    # Check that the mocked functions were called correctly
    mock_wildcard.assert_called_once_with(domain, ANY)
    initial_subs = {'passive.example.com', 'active.example.com'}
    raw_subs = initial_subs.union({'permute.example.com'})
    mock_resolve.assert_called_once_with(raw_subs, {'1.2.3.4'}, ANY)

    # Assert that the new functions were called with the correct args
    all_final_domains = resolved_domains.union({'code.example.com'})
    mock_resolve_ips.assert_called_once_with(all_final_domains, ANY)

    # The IPs passed to the ASN lookup should be the values from the ip_map
    all_ips = set()
    for ip_list in mock_ip_map.values():
        all_ips.update(ip_list)
    mock_get_asn.assert_called_once_with(all_ips)

    # Teardown any directories that might have been created by mocked functions
    output_dir = config['recon_output_dir']
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)


@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.subprocess.run')
def test_resolve_and_validate_with_wildcard_filtering(mock_run):
    """
    Tests the wildcard filtering logic within the resolve_and_validate function.
    """
    from cyberhunter_3d.core.reconnaissance.subdomain_enum import resolve_and_validate
    from cyberhunter_3d.utils.logger import setup_logger

    mock_logger = setup_logger('TestResolve', 'test_resolve.log')

    # Mock the output of the two subprocess calls made by the function
    puredns_output = "good.example.com\nwildcard.example.com\nanother.good.example.com"
    dnsx_output = (
        "good.example.com [8.8.8.8]\n"
        "wildcard.example.com [1.2.3.4]\n"
        "another.good.example.com [8.8.4.4]\n"
    )
    mock_run.side_effect = [
        MagicMock(stdout=puredns_output, stderr="", returncode=0, check_returncode=lambda: None), # puredns call
        MagicMock(stdout=dnsx_output, stderr="", returncode=0, check_returncode=lambda: None)  # dnsx call
    ]

    initial_subdomains = {'good.example.com', 'wildcard.example.com', 'another.good.example.com'}
    wildcard_ips = {'1.2.3.4'} # This is the IP to be filtered

    validated_subdomains = resolve_and_validate(initial_subdomains, wildcard_ips, mock_logger)

    # Assert that the subdomain resolving to the wildcard IP was removed
    assert validated_subdomains == {'good.example.com', 'another.good.example.com'}
    assert 'wildcard.example.com' not in validated_subdomains
    assert mock_run.call_count == 2


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
