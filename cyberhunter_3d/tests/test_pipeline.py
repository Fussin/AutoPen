import pytest
import json
from unittest.mock import patch, MagicMock, ANY
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2

# Mock Finding format that the plugins are expected to return
def create_mock_finding(target, tool, phase, status="success", evidence=None, error=None):
    """Creates a mock Finding object."""
    return {"target": target, "phase": phase, "tool": tool, "status": status, "evidence": evidence, "error": error}

@patch('cyberhunter_3d.core.reconnaissance.js_engine.run_github_dorking', return_value=[])
@patch('cyberhunter_3d.core.reconnaissance.cloud_asset_enum.find_cloud_assets', return_value={})
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_js_enumeration')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_enrichment_engine')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.resolve_and_validate')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_active_enumeration')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_passive_enumeration')
def test_full_pipeline_orchestration(
    mock_passive, mock_active, mock_resolve, mock_enrich, mock_js, mock_cloud, mock_github, tmp_path
):
    """
    Tests that the main orchestrator (`enumerate_subdomains_v2`) correctly
    integrates all refactored engines and produces the correct final report.
    """
    # Arrange
    mock_passive.return_value = [create_mock_finding("passive.example.com", "subfinder", "recon-passive", evidence={"poc": "passive.example.com"})]
    mock_active.return_value = [create_mock_finding("active.example.com", "gobuster", "recon-active", evidence={"poc": "active.example.com"})]
    validated_hosts = {"passive.example.com", "active.example.com"}
    mock_resolve.return_value = validated_hosts
    mock_enrich.return_value = [
        create_mock_finding("http://passive.example.com", "gowitness", "enrichment-screenshot", evidence={"screenshot_dir": "..."}),
        create_mock_finding("active.example.com", "nmap-scan", "enrichment-service-scan", evidence={"port": "443", "service_info": "nginx"})
    ]
    mock_js.return_value = [
        create_mock_finding("http://active.example.com", "linkfinder", "js-analysis", evidence={"endpoint": "/api/v2/users"})
    ]

    # Act
    with patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.load_config') as mock_load_config:
        mock_load_config.return_value = {
            'recon_output_dir': str(tmp_path),
            'final_recon_file': f"{tmp_path}/final_report.json",
            'subdomains_all_file': f"{tmp_path}/subs_all.txt",
            'master_subdomains_file': f"{tmp_path}/subs_master.txt",
            'subdomains_metadata_file': f"{tmp_path}/subs_meta.json",
            'tools': {}, 'wordlists': {'resolvers': 'dummy.txt'}
        }
        enumerate_subdomains_v2("example.com")

    # Assert
    final_report_path = tmp_path / "final_report.json"
    assert final_report_path.exists()
    with open(final_report_path, 'r') as f:
        data = json.load(f)

    assert "passive.example.com" in data['master_subdomains']
    assert len(data['screenshots']) == 1
    assert "active.example.com" in data['technology_and_ports']
    assert data['technology_and_ports']['active.example.com']['ports'][0]['service_info'] == "nginx"
    assert len(data['js_findings']) == 1
    assert data['js_findings'][0]['evidence']['endpoint'] == "/api/v2/users"
