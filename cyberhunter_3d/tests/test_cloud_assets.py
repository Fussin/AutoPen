import pytest
from unittest.mock import patch, MagicMock, call, ANY
from cyberhunter_3d.core.reconnaissance.cloud_asset_enum import find_cloud_assets

def create_mock_finding(target, tool, phase, status="success", evidence=None, error=None):
    return {"target": target, "phase": phase, "tool": tool, "status": status, "evidence": evidence, "error": error}

@patch('cyberhunter_3d.core.reconnaissance.cloud_asset_enum.S3ScannerPlugin')
@patch('cyberhunter_3d.core.reconnaissance.cloud_asset_enum.GoblobPlugin')
def test_cloud_asset_engine_orchestration(mock_goblob, mock_s3scanner):
    """
    Tests that the cloud asset engine correctly orchestrates its plugins.
    """
    initial_subdomains = {"test.example.com", "prod.example.com"}

    mock_goblob.return_value.run.return_value = [
        create_mock_finding("testexample", "goblob", "cloud-asset-enum-azure", evidence={"azure_blob": "testexample"})
    ]

    mock_s3scanner.return_value.run.side_effect = [
        [create_mock_finding("prod-bucket", "s3scanner-aws", "cloud-asset-enum-s3-gcp", evidence={"aws_bucket": "prod-bucket"})],
        [create_mock_finding("test-bucket", "s3scanner-gcp", "cloud-asset-enum-s3-gcp", evidence={"gcp_bucket": "test-bucket"})],
    ]

    all_findings = find_cloud_assets(initial_subdomains)

    assert len(all_findings) == 3
    mock_goblob.return_value.run.assert_called_once()

    # Use ANY to assert that the method was called with a list, without specifying the exact list
    mock_s3scanner.return_value.run.assert_has_calls([
        call(ANY, provider='aws'),
        call(ANY, provider='gcp')
    ], any_order=True)

    tools_found = {f['tool'] for f in all_findings}
    assert "goblob" in tools_found
    assert "s3scanner-aws" in tools_found
    assert "s3scanner-gcp" in tools_found
