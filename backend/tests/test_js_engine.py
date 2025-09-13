import pytest
from unittest.mock import patch, MagicMock, ANY
from cyberhunter_3d.core.reconnaissance.js_engine import run_js_enumeration

# Mock Finding format that the plugins are expected to return
def create_mock_finding(target, tool, phase, status="success", evidence=None, error=None):
    """Creates a mock Finding object."""
    return {"target": target, "phase": phase, "tool": tool, "status": status, "evidence": evidence, "error": error}

@patch('cyberhunter_3d.core.reconnaissance.js_engine.NucleiJsSecretsPlugin')
@patch('cyberhunter_3d.core.reconnaissance.js_engine.LinkfinderPlugin')
def test_js_engine_orchestration(mock_linkfinder, mock_nuclei):
    """
    Tests that the JS engine correctly orchestrates its plugins.
    """
    # Arrange
    live_hosts = {"http://test1.example.com", "http://test2.example.com"}

    # Mock Linkfinder to return one finding for each host
    mock_linkfinder.return_value.run.side_effect = [
        [create_mock_finding("http://test1.example.com", "linkfinder", "js-analysis-endpoints", evidence={"endpoint": "/api/v1"})],
        [create_mock_finding("http://test2.example.com", "linkfinder", "js-analysis-endpoints", evidence={"endpoint": "/api/v2"})],
    ]

    # Mock Nuclei to return one finding
    mock_nuclei.return_value.run.return_value = [
        create_mock_finding("http://test1.example.com", "nuclei-js-secrets", "js-analysis-secrets", evidence={"template": "generic-api-key"})
    ]

    # Act
    all_findings = run_js_enumeration(live_hosts)

    # Assert
    assert len(all_findings) == 3 # 2 from linkfinder, 1 from nuclei

    # Check that linkfinder was called for each host
    assert mock_linkfinder.return_value.run.call_count == 2

    # Check that nuclei was called once with all hosts
    mock_nuclei.return_value.run.assert_called_once_with(list(live_hosts))

    # Check the content of the findings
    tools_found = {f['tool'] for f in all_findings}
    assert "linkfinder" in tools_found
    assert "nuclei-js-secrets" in tools_found
