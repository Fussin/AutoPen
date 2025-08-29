import pytest
import os
import json
import shutil
from unittest.mock import patch, MagicMock, ANY, call
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.plugins.base import Plugin

class MockPlugin(Plugin):
    def __init__(self, name, description, results):
        self._name = name
        self._description = description
        self.results = results

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def run(self, target: str, **kwargs) -> dict:
        return self.results

@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.save_to_json')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.PluginManager')
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.resolve_and_validate', return_value={"passive.example.com", "active.example.com"})
@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.detect_wildcard_ips', return_value=set())
def test_full_recon_pipeline_with_plugins(
    mock_detect_wildcard, mock_resolve_and_validate, mock_plugin_manager, mock_save_json
):
    """
    Integration test for the new plugin-based reconnaissance pipeline.
    """
    # 1. Setup Mock Plugins
    mock_plugins = [
        MockPlugin("Passive Enumeration", "", {"passive_subdomains": {"passive.example.com"}}),
        MockPlugin("Active Enumeration", "", {"active_subdomains": {"active.example.com"}}),
        MockPlugin("Subdomain Takeover", "", {"takeover_vulnerabilities": [{"host": "takeover.example.com"}]}),
    ]
    mock_plugin_manager.return_value.get_all_plugins.return_value = mock_plugins

    # 2. Execute the function
    domain = "example.com"
    output_files = enumerate_subdomains_v2(domain)

    # 3. Assertions
    # A simplified check to ensure the pipeline runs and calls save_to_json
    mock_save_json.assert_called()
