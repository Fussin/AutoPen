import pytest
from unittest.mock import patch, MagicMock, call
from cyberhunter_3d.core.reconnaissance.subdomain_enum import perform_delta_scan
from cyberhunter_3d.utils.logger import setup_logger

logger = setup_logger('TestDeltaScan', 'test_delta_scan.log')

@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.save_to_json')
def test_perform_delta_scan(mock_save_to_json):
    """
    Tests that the perform_delta_scan function correctly identifies new and
    removed subdomains and calls the save_to_json function with the correct data.
    """
    master_subdomains = {"a.example.com", "b.example.com", "c.example.com"}
    previous_subdomains = {"a.example.com", "d.example.com"}

    mock_save_to_json.return_value = "/fake/path/to/file.json"

    delta_paths = perform_delta_scan(master_subdomains, previous_subdomains, logger)

    expected_new = {"b.example.com", "c.example.com"}
    expected_removed = {"d.example.com"}

    assert mock_save_to_json.call_count == 2

    # Check the call for new subdomains
    call_for_new = next((c for c in mock_save_to_json.call_args_list if c.args[1] == 'new_subdomains.json'), None)
    assert call_for_new is not None
    assert set(call_for_new.args[0]) == expected_new

    # Check the call for removed subdomains
    call_for_removed = next((c for c in mock_save_to_json.call_args_list if c.args[1] == 'removed_subdomains.json'), None)
    assert call_for_removed is not None
    assert set(call_for_removed.args[0]) == expected_removed

    assert "new_subdomains" in delta_paths
    assert "removed_subdomains" in delta_paths

@patch('cyberhunter_3d.core.reconnaissance.subdomain_enum.save_to_json')
def test_perform_delta_scan_no_previous_subdomains(mock_save_to_json):
    """
    Tests that the delta scan function does nothing if there are no
    previous subdomains to compare against.
    """
    master_subdomains = {"a.example.com", "b.example.com"}
    previous_subdomains = set()

    delta_paths = perform_delta_scan(master_subdomains, previous_subdomains, logger)

    assert delta_paths == {}
    mock_save_to_json.assert_not_called()
