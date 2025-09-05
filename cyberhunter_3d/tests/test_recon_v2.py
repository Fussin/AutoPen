import pytest
import json
from unittest.mock import patch, MagicMock, ANY
from cyberhunter_3d.core.reconnaissance.passive_engine import run_passive_enumeration
from cyberhunter_3d.core.reconnaissance.active_engine import run_active_enumeration
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2

# Mock Finding format that the plugins are expected to return
def create_mock_finding(subdomain, tool, target="example.com", status="success", error=None):
    """Creates a mock Finding object."""
    return {
        "target": target, "phase": "recon", "tool": tool,
        "status": status, "evidence": {"poc": subdomain} if status == "success" else None, "error": error,
    }

@patch('cyberhunter_3d.core.reconnaissance.passive_engine.AssetfinderPlugin')
@patch('cyberhunter_3d.core.reconnaissance.passive_engine.AmassPlugin')
@patch('cyberhunter_3d.core.reconnaissance.passive_engine.SubfinderPlugin')
def test_passive_engine_returns_findings_list(mock_subfinder, mock_amass, mock_assetfinder):
    """Tests that the passive engine returns a list of Finding objects."""
    # Arrange
    mock_subfinder.return_value.run.return_value = [create_mock_finding("sub1.example.com", "subfinder")]
    mock_amass.return_value.run.return_value = [create_mock_finding("sub2.example.com", "amass", status="failed", error="timeout")]
    mock_assetfinder.return_value.run.return_value = []

    # Act
    result_findings = run_passive_enumeration("example.com")

    # Assert
    assert isinstance(result_findings, list)
    assert len(result_findings) == 2
    # Check for content without assuming order
    statuses = sorted([f['status'] for f in result_findings])
    assert statuses == ['failed', 'success']


@patch('cyberhunter_3d.core.reconnaissance.active_engine.NmapDnsPlugin')
@patch('cyberhunter_3d.core.reconnaissance.active_engine.PureDNSPlugin')
@patch('cyberhunter_3d.core.reconnaissance.active_engine.GobusterPlugin')
def test_active_engine_returns_findings_list(mock_gobuster, mock_puredns, mock_nmap):
    """Tests that the active engine returns a list of Finding objects."""
    # Arrange
    mock_gobuster.return_value.check_dependencies.return_value = True
    mock_gobuster.return_value.run.return_value = [create_mock_finding("active1.example.com", "gobuster")]
    mock_puredns.return_value.check_dependencies.return_value = True
    mock_puredns.return_value.run.return_value = []
    mock_nmap.return_value.check_dependencies.return_value = True
    mock_nmap.return_value.run.return_value = []

    # Act
    result_findings = run_active_enumeration("example.com")

    # Assert
    assert isinstance(result_findings, list)
    assert len(result_findings) == 1
    assert result_findings[0]['tool'] == 'gobuster'

@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_visual_recon', return_value=([], {}))
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.resolve_and_validate')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_permutation_enumeration', return_value=set())
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_active_enumeration')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_passive_enumeration')
def test_enumerate_subdomains_v2_orchestrator(mock_passive, mock_active, mock_perm, mock_resolve, mock_visual, tmp_path):
    """Tests that the main orchestrator produces the correct output files."""
    # Arrange
    # Mock engine outputs
    mock_passive.return_value = [
        create_mock_finding("passive1.example.com", "subfinder"),
        create_mock_finding("shared.example.com", "amass"),
        create_mock_finding("passive-fail.example.com", "assetfinder", status="failed", error="timeout"),
    ]
    mock_active.return_value = [
        create_mock_finding("active1.example.com", "gobuster"),
        create_mock_finding("shared.example.com", "puredns"), # duplicate
    ]

    # Mock resolver to return a subset of the raw domains
    mock_resolve.return_value = {"passive1.example.com", "shared.example.com"}

    # Act
    # We patch load_config specifically for this test to inject our temp path
    with patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.load_config') as mock_load_config:
        mock_load_config.return_value = {
            'recon_output_dir': str(tmp_path),
            'subdomains_all_file': f"{tmp_path}/subs_all.txt",
            'subdomains_metadata_file': f"{tmp_path}/subs_meta.json",
            'master_subdomains_file': f"{tmp_path}/subs_master.txt",
            'tools': {}, 'wordlists': {} # Add dummy keys for resolve_and_validate
        }
        enumerate_subdomains_v2("example.com")

    # Assert
    all_file = tmp_path / "subs_all.txt"
    meta_file = tmp_path / "subs_meta.json"
    master_file = tmp_path / "subs_master.txt"

    assert all_file.exists()
    assert meta_file.exists()
    assert master_file.exists()

    with open(all_file, 'r') as f:
        content = f.read().strip().split('\n')
    assert sorted(content) == ["active1.example.com", "passive1.example.com", "shared.example.com"]

    with open(master_file, 'r') as f:
        content = f.read().strip().split('\n')
    assert sorted(content) == ["passive1.example.com", "shared.example.com"]

    with open(meta_file, 'r') as f:
        metadata = json.load(f)
    assert metadata['domain'] == "example.com"
    assert metadata['plugin_stats']['assetfinder']['failed'] == 1
    assert len(metadata['errors']) == 1
