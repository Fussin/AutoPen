import pytest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2

@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_passive_enumeration')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_active_enumeration')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_permutation_enumeration')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.resolve_and_validate')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_visual_recon')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_js_enumeration')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_tech_fingerprinting')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.find_cloud_assets')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.run_github_dorking')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.load_config')
def test_enumerate_subdomains_v2_flow(mock_load_config, mock_github, mock_cloud, mock_tech, mock_js, mock_visual, mock_resolve, mock_permute, mock_active, mock_passive):
    """
    Tests the flow of enumerate_subdomains_v2 with all dependencies mocked.
    """
    # Setup mocks
    mock_load_config.return_value = {
        'recon_output_dir': '/tmp',
        'master_subdomains_file': 'master.txt',
        'final_recon_file': 'final.json'
    }
    mock_passive.return_value = {"test.example.com"}
    mock_active.return_value = {"active.example.com"}
    mock_permute.return_value = {"permute.example.com"}
    mock_resolve.return_value = {"test.example.com", "active.example.com", "permute.example.com"}
    mock_visual.return_value = (["http://test.example.com"], "/tmp/screenshots")
    mock_js.return_value = []
    mock_tech.return_value = {}
    mock_cloud.return_value = {}
    mock_github.return_value = []

    # Run the function
    assets = enumerate_subdomains_v2("example.com")

    # Assertions
    assert len(assets) == 3
    mock_passive.assert_called_once_with("example.com")
    mock_active.assert_called_once_with("example.com")
    mock_permute.assert_called_once()
    mock_resolve.assert_called_once()
    mock_visual.assert_called_once()
