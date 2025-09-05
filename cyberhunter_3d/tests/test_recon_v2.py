import pytest
from unittest.mock import patch, MagicMock, ANY
from cyberhunter_3d.core.reconnaissance.passive_engine import run_passive_enumeration
from cyberhunter_3d.core.reconnaissance.active_engine import run_active_enumeration

# Mock Finding format that the plugins are expected to return
def create_mock_finding(subdomain, tool, target="example.com"):
    return {
        "target": target,
        "phase": "recon",
        "tool": tool,
        "evidence": {"poc": subdomain},
    }

@patch('cyberhunter_3d.core.reconnaissance.passive_engine.AssetfinderPlugin')
@patch('cyberhunter_3d.core.reconnaissance.passive_engine.AmassPlugin')
@patch('cyberhunter_3d.core.reconnaissance.passive_engine.SubfinderPlugin')
def test_passive_engine_with_plugin_mocks(mock_subfinder, mock_amass, mock_assetfinder):
    """
    Tests the passive engine's orchestration of all its plugins.
    """
    mock_subfinder.return_value.name.return_value = "subfinder"
    mock_subfinder.return_value.check_dependencies.return_value = True
    mock_subfinder.return_value.run.return_value = [create_mock_finding("sub1.example.com", "subfinder")]
    mock_amass.return_value.name.return_value = "amass"
    mock_amass.return_value.check_dependencies.return_value = True
    mock_amass.return_value.run.return_value = [create_mock_finding("sub2.example.com", "amass")]
    mock_assetfinder.return_value.name.return_value = "assetfinder"
    mock_assetfinder.return_value.check_dependencies.return_value = True
    mock_assetfinder.return_value.run.return_value = []

    result_subdomains = run_passive_enumeration("example.com")

    assert result_subdomains == {"sub1.example.com", "sub2.example.com"}

@patch('cyberhunter_3d.core.reconnaissance.active_engine.NmapDnsPlugin')
@patch('cyberhunter_3d.core.reconnaissance.active_engine.PureDNSPlugin')
@patch('cyberhunter_3d.core.reconnaissance.active_engine.GobusterPlugin')
def test_active_engine_with_plugin_mocks(mock_gobuster, mock_puredns, mock_nmap):
    """
    Tests the active engine's orchestration of plugins.
    """
    mock_gobuster.return_value.name.return_value = "gobuster"
    mock_gobuster.return_value.check_dependencies.return_value = True
    mock_gobuster.return_value.run.return_value = [create_mock_finding("active1.example.com", "gobuster")]
    mock_puredns.return_value.name.return_value = "puredns"
    mock_puredns.return_value.check_dependencies.return_value = True
    mock_puredns.return_value.run.return_value = [create_mock_finding("active2.example.com", "puredns")]
    mock_nmap.return_value.name.return_value = "nmap_dns"
    mock_nmap.return_value.check_dependencies.return_value = True
    mock_nmap.return_value.run.return_value = [create_mock_finding("active3.example.com", "nmap_dns")]

    result_subdomains = run_active_enumeration("example.com")

    assert result_subdomains == {"active1.example.com", "active2.example.com", "active3.example.com"}
