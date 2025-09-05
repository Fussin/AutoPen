import pytest
from unittest.mock import patch, MagicMock, ANY
from cyberhunter_3d.core.reconnaissance.passive_engine import run_passive_enumeration
from cyberhunter_3d.core.reconnaissance.active_engine import run_active_enumeration

# Mock Finding format that the plugins are expected to return
def create_mock_finding(subdomain, tool, target="example.com"):
    """Creates a mock for a successful finding."""
    return {
        "target": target, "phase": "recon", "tool": tool,
        "status": "success", "evidence": {"poc": subdomain}, "error": None,
    }

def create_failed_finding(tool, error_msg, target="example.com"):
    """Creates a mock for a failed finding."""
    return {
        "target": target, "phase": "recon", "tool": tool,
        "status": "failed", "evidence": None, "error": error_msg,
    }

@patch('cyberhunter_3d.core.reconnaissance.passive_engine.AssetfinderPlugin')
@patch('cyberhunter_3d.core.reconnaissance.passive_engine.AmassPlugin')
@patch('cyberhunter_3d.core.reconnaissance.passive_engine.SubfinderPlugin')
def test_passive_engine_with_plugin_mocks(mock_subfinder, mock_amass, mock_assetfinder):
    """Tests the passive engine's orchestration of plugins and resilience arg passing."""
    # Arrange
    mock_subfinder.return_value.run.return_value = [create_mock_finding("sub1.example.com", "subfinder")]
    mock_amass.return_value.run.return_value = [create_mock_finding("sub2.example.com", "amass")]
    mock_assetfinder.return_value.run.return_value = []

    # Act
    result_subdomains = run_passive_enumeration("example.com")

    # Assert
    assert result_subdomains == {"sub1.example.com", "sub2.example.com"}
    mock_subfinder.return_value.run.assert_called_once_with(["example.com"], retries=ANY, timeout=ANY)
    mock_amass.return_value.run.assert_called_once_with(["example.com"], retries=ANY, timeout=ANY)

@patch('cyberhunter_3d.core.reconnaissance.passive_engine.AssetfinderPlugin')
@patch('cyberhunter_3d.core.reconnaissance.passive_engine.AmassPlugin')
@patch('cyberhunter_3d.core.reconnaissance.passive_engine.SubfinderPlugin')
def test_passive_engine_handles_plugin_failure(mock_subfinder, mock_amass, mock_assetfinder, caplog):
    """Tests that the passive engine handles a structured failure from a plugin gracefully."""
    # Arrange
    mock_subfinder.return_value.name.return_value = "subfinder"
    mock_subfinder.return_value.run.return_value = [create_mock_finding("good.example.com", "subfinder")]

    mock_amass.return_value.name.return_value = "amass"
    mock_amass.return_value.run.return_value = [create_failed_finding("amass", "Tool timed out")]

    mock_assetfinder.return_value.name.return_value = "assetfinder"
    mock_assetfinder.return_value.run.return_value = []

    # Act
    result_subdomains = run_passive_enumeration("example.com")

    # Assert
    assert result_subdomains == {"good.example.com"} # Only the successful finding should be included
    assert "Plugin amass failed on target example.com: Tool timed out" in caplog.text

@patch('cyberhunter_3d.core.reconnaissance.active_engine.NmapDnsPlugin')
@patch('cyberhunter_3d.core.reconnaissance.active_engine.PureDNSPlugin')
@patch('cyberhunter_3d.core.reconnaissance.active_engine.GobusterPlugin')
def test_active_engine_with_plugin_mocks(mock_gobuster, mock_puredns, mock_nmap):
    """Tests the active engine's orchestration and resilience arg passing."""
    # Arrange
    mock_gobuster.return_value.check_dependencies.return_value = True
    mock_gobuster.return_value.run.return_value = [create_mock_finding("active1.example.com", "gobuster")]

    mock_puredns.return_value.check_dependencies.return_value = True
    mock_puredns.return_value.run.return_value = [create_mock_finding("active2.example.com", "puredns")]

    mock_nmap.return_value.check_dependencies.return_value = True
    mock_nmap.return_value.run.return_value = []

    # Act
    result_subdomains = run_active_enumeration("example.com")

    # Assert
    assert result_subdomains == {"active1.example.com", "active2.example.com"}
    mock_gobuster.return_value.run.assert_called_once_with([ANY], wordlist=ANY, retries=ANY, timeout=ANY)
    mock_puredns.return_value.run.assert_called_once_with([ANY], wordlist=ANY, resolvers=ANY, retries=ANY, timeout=ANY)
    mock_nmap.return_value.run.assert_called_once_with([ANY], retries=ANY, timeout=ANY)
