import pytest
from unittest.mock import patch, MagicMock
from cyberhunter_3d.core.reconnaissance.utils import detect_wildcard_ips
from cyberhunter_3d.utils.logger import setup_logger

# Use a single logger instance for all tests in this file
logger = setup_logger('TestUtils', 'test_utils.log')

@patch('cyberhunter_3d.core.reconnaissance.utils.subprocess.run')
def test_detect_wildcard_ips_positive_case(mock_run):
    """
    Tests that detect_wildcard_ips correctly identifies and returns wildcard IPs.
    """
    # Mock the return value of the subprocess call to dnsx
    mock_process = MagicMock()
    mock_process.stdout = (
        "random1.example.com [1.2.3.4]\n"
        "random2.example.com [1.2.3.4]\n"
        "random3.example.com [5.6.7.8]\n"
    )
    mock_run.return_value = mock_process

    domain = "example.com"
    wildcard_ips = detect_wildcard_ips(domain, logger)

    # Assert that the function returns the correct set of unique IPs
    assert wildcard_ips == {'1.2.3.4', '5.6.7.8'}
    mock_run.assert_called_once()

@patch('cyberhunter_3d.core.reconnaissance.utils.subprocess.run')
def test_detect_wildcard_ips_negative_case(mock_run):
    """
    Tests that detect_wildcard_ips returns an empty set when no wildcard is detected.
    """
    # Mock the return value of the subprocess call to dnsx for no resolved domains
    mock_process = MagicMock()
    mock_process.stdout = ""
    mock_run.return_value = mock_process

    domain = "example.com"
    wildcard_ips = detect_wildcard_ips(domain, logger)

    # Assert that the function returns an empty set
    assert wildcard_ips == set()
    mock_run.assert_called_once()

@patch('cyberhunter_3d.core.reconnaissance.utils.subprocess.run')
def test_detect_wildcard_ips_tool_not_found(mock_run):
    """
    Tests that detect_wildcard_ips handles a FileNotFoundError gracefully.
    """
    # Simulate the tool not being found
    mock_run.side_effect = FileNotFoundError

    domain = "example.com"
    wildcard_ips = detect_wildcard_ips(domain, logger)

    # Assert that the function returns an empty set and logs an error
    assert wildcard_ips == set()
    mock_run.assert_called_once()

from cyberhunter_3d.core.reconnaissance.utils import resolve_subdomains_to_ips

@patch('cyberhunter_3d.core.reconnaissance.utils.subprocess.run')
def test_resolve_subdomains_to_ips(mock_run):
    """
    Tests that resolve_subdomains_to_ips correctly resolves subdomains and parses the JSON.
    """
    dnsx_output = (
        '{"host":"a.example.com","a":["1.1.1.1","2.2.2.2"]}\n'
        '{"host":"b.example.com","a":["3.3.3.3"]}\n'
    )
    mock_process = MagicMock()
    mock_process.stdout = dnsx_output
    mock_run.return_value = mock_process

    subdomains = {'a.example.com', 'b.example.com'}
    ip_mapping = resolve_subdomains_to_ips(subdomains, logger)

    assert len(ip_mapping) == 2
    assert ip_mapping['a.example.com'] == ['1.1.1.1', '2.2.2.2']
    assert ip_mapping['b.example.com'] == ['3.3.3.3']
    mock_run.assert_called_once()
