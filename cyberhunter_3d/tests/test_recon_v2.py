import pytest
from unittest.mock import patch, MagicMock, ANY
from cyberhunter_3d.core.reconnaissance.passive_engine import run_passive_enumeration
from cyberhunter_3d.core.reconnaissance.active_engine import run_active_enumeration

# Mock Finding format that the plugins are expected to return
def create_mock_finding(subdomain, tool, target="example.com", status="success", error=None):
    """Creates a mock Finding object."""
    return {
        "target": target,
        "phase": "recon",
        "tool": tool,
        "status": status,
        "evidence": {"poc": subdomain} if status == "success" else None,
        "error": error,
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


from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2

@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.resolve_and_validate', side_effect=lambda x: x) # Mock resolve to return its input
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.GotatorPlugin')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.DnsgenPlugin')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_active_enumeration')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_passive_enumeration')
def test_enumerate_subdomains_v2_orchestrator(
    mock_passive, mock_active, mock_dnsgen, mock_gotator, mock_resolve
):
    """
    Tests that the main orchestrator correctly calls all enumeration engines,
    including the new permutation plugins.
    """
    # Arrange
    mock_passive.return_value = {"passive1.example.com", "shared.example.com"}
    mock_active.return_value = {"active1.example.com", "shared.example.com"}

    mock_dnsgen.return_value.run.return_value = [
        create_mock_finding("dnsgen1.example.com", "dnsgen"),
    ]
    mock_gotator.return_value.run.return_value = [
        create_mock_finding("gotator1.example.com", "gotator"),
    ]

    # Act
    # We need to mock load_config as well since it's called inside the function
    with patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.load_config') as mock_load_config:
        mock_load_config.return_value = {'wordlists': {'dns_bruteforce': 'dummy.txt'}}

        # Mocking os.path.exists for the combined wordlist part
        with patch('os.path.exists', return_value=True):
            result_assets = enumerate_subdomains_v2("example.com")

    # Assert
    # Check that the permutation plugins were called
    mock_dnsgen.return_value.run.assert_called_once()
    mock_gotator.return_value.run.assert_called_once()

    # Check the final aggregated results
    final_subdomains = {asset['value'] for asset in result_assets}
    expected_subdomains = {
        "passive1.example.com", "shared.example.com",
        "active1.example.com", "dnsgen1.example.com", "gotator1.example.com"
    }
    assert final_subdomains == expected_subdomains
