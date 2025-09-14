import pytest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.dorking.github_dorking_engine import run_github_dorking_engine

def create_mock_finding(target, tool, phase, status="success", evidence=None, error=None):
    return {"target": target, "phase": phase, "tool": tool, "status": status, "evidence": evidence, "error": error}

@patch('cyberhunter_3d.core.dorking.github_dorking_engine.GhDorkPlugin')
def test_github_dorking_engine_orchestration(mock_gh_dork):
    """
    Tests that the github dorking engine correctly orchestrates its plugin.
    """
    # Arrange
    initial_subdomains = {"test.example.com", "prod.example.com"}

    mock_gh_dork.return_value.run.return_value = [
        create_mock_finding("github", "gh-dork", "dorking-github", evidence={"dork_result": "some secret found"})
    ]

    # Act
    all_findings = run_github_dorking_engine(initial_subdomains)

    # Assert
    assert len(all_findings) == 1

    # Check that the plugin was called with the correct org names
    expected_orgs = ['example', 'prod']
    mock_gh_dork.return_value.run.assert_called_once()
    # A more robust test could inspect the list passed to the run method

    assert all_findings[0]['evidence']['dork_result'] == "some secret found"
