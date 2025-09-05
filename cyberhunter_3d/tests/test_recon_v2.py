import pytest
import json
from unittest.mock import patch, MagicMock, ANY
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2

# Mock Finding format that the plugins are expected to return
def create_mock_finding(subdomain, tool, target="example.com", status="success", error=None, phase="recon"):
    """Creates a mock Finding object."""
    return {
        "target": target, "phase": phase, "tool": tool,
        "status": status, "evidence": {"poc": subdomain} if status == "success" else None, "error": error,
    }

@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_visual_recon', return_value=([], {}))
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.resolve_and_validate')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.GotatorPlugin')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.DnsgenPlugin')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_active_enumeration')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_passive_enumeration')
def test_enumerate_subdomains_v2_orchestrator(
    mock_passive, mock_active, mock_dnsgen, mock_gotator, mock_resolve, mock_visual, tmp_path
):
    """
    Tests that the main orchestrator correctly calls all engines,
    including permutation plugins, and produces the correct output files and metadata.
    """
    # Arrange
    # Mock engine outputs
    mock_passive.return_value = [
        create_mock_finding("passive1.example.com", "subfinder"),
        create_mock_finding("shared.example.com", "amass"),
    ]
    mock_active.return_value = [
        create_mock_finding("active1.example.com", "gobuster"),
    ]

    # Mock permutation plugin outputs
    mock_dnsgen.return_value.run.return_value = [
        create_mock_finding("dnsgen1.example.com", "dnsgen", phase="recon-permutation"),
    ]
    mock_gotator.return_value.run.return_value = [
        create_mock_finding("gotator-fail.example.com", "gotator", status="failed", error="timeout", phase="recon-permutation"),
    ]

    # Mock resolver to return a subset of the raw domains
    mock_resolve.return_value = {"passive1.example.com", "shared.example.com", "dnsgen1.example.com"}

    # Act
    with patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.load_config') as mock_load_config:
        mock_load_config.return_value = {
            'recon_output_dir': str(tmp_path),
            'subdomains_all_file': f"{tmp_path}/subs_all.txt",
            'subdomains_metadata_file': f"{tmp_path}/subs_meta.json",
            'master_subdomains_file': f"{tmp_path}/subs_master.txt",
            'wordlists': {'dns_bruteforce': 'dummy_wordlist.txt'},
            'tools': {},
        }
        enumerate_subdomains_v2("example.com")

    # Assert
    # Check that the output files were created
    all_file = tmp_path / "subs_all.txt"
    meta_file = tmp_path / "subs_meta.json"
    master_file = tmp_path / "subs_master.txt"

    assert all_file.exists()
    assert meta_file.exists()
    assert master_file.exists()

    # Check content of raw subdomains file (should include permutation results)
    with open(all_file, 'r') as f:
        content = f.read().strip().split('\n')
    assert sorted(content) == ["active1.example.com", "dnsgen1.example.com", "passive1.example.com", "shared.example.com"]

    # Check content of master (validated) subdomains file
    with open(master_file, 'r') as f:
        content = f.read().strip().split('\n')
    assert sorted(content) == ["dnsgen1.example.com", "passive1.example.com", "shared.example.com"]

    # Check content of metadata file for permutation stats
    with open(meta_file, 'r') as f:
        metadata = json.load(f)

    dnsgen_stats = metadata['plugin_stats']['dnsgen']
    gotator_stats = metadata['plugin_stats']['gotator']

    assert dnsgen_stats['success'] == 1
    assert dnsgen_stats['input_count'] == 3 # passive1, shared, active1
    assert dnsgen_stats['output_count'] == 1

    assert gotator_stats['failed'] == 1
    assert gotator_stats['input_count'] == 3
    assert gotator_stats['output_count'] == 0
    assert len(metadata['errors']) == 1
    assert metadata['errors'][0]['tool'] == 'gotator'
